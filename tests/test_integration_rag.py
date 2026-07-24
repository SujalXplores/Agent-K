"""Live-database integration tests (requires the running rag-postgres container).

Every other test in this phase mocks AsyncSession.execute, so the pgvector
SQL is never compiled or executed - a production-breaking adapter conflict
(app/db.py registering a connection-level pgvector codec alongside the
pgvector.sqlalchemy Vector ORM type) passed 18 green tests while every real
POST /ask returned HTTP 500 (02-VERIFICATION.md gap 1). This module executes
real SQL against the live corpus so that reintroducing that class of defect
fails a test instead of shipping silently.

Skips (does not error) when no live database is reachable, so the mocked
unit suite stays runnable on a machine with no Docker.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import AsyncSessionLocal, get_engine
from app.models import Document
from app.rag import retrieve

pytestmark = pytest.mark.integration


def _live_corpus_doc_count() -> int | None:
    """Return the live `documents` row count, or None if unreachable.

    Disposes the shared engine's connection pool at the end of its own
    asyncio.run() loop: asyncpg connections are bound to the event loop
    that created them, and this precheck's loop is closed before the
    test session's loop starts, so leaving pooled connections behind
    causes a later "another operation is in progress" InterfaceError
    when a test tries to reuse a connection bound to a dead loop.
    """
    try:

        async def _count() -> int:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(func.count()).select_from(Document))
                count = result.scalar_one()
            await get_engine().dispose()
            return count

        return asyncio.run(_count())
    except Exception:
        return None


_doc_count = _live_corpus_doc_count()
if not _doc_count:
    pytest.skip(
        "live rag-postgres database not reachable or not seeded - start it "
        "and run `python -m scripts.seed_corpus` to enable these tests "
        "(container: rag-postgres)",
        allow_module_level=True,
    )


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_between_tests():
    """Dispose the shared engine's connection pool after every test.

    asyncpg connections are bound to the event loop that created them.
    pytest-asyncio gives each test its own loop, and the synchronous
    TestClient-driven tests in this module run the /ask handler on yet
    another (anyio) loop, so a pooled connection left over from a prior
    test's loop raises "attached to a different loop" / "another
    operation is in progress" the next time it is checked out. Disposing
    after each test forces a fresh connection on the next loop.
    """
    yield
    await get_engine().dispose()


@pytest_asyncio.fixture
async def live_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def live_client():
    from app.main import app as fastapi_app

    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_retrieve_executes_real_pgvector_query_against_live_corpus(live_session):
    # Regression guard for the app/db.py adapter conflict: if a
    # connection-level pgvector codec is reintroduced, this raises
    # DBAPIError wrapping asyncpg.exceptions.DataError instead of passing.
    docs = await retrieve(live_session, "How do I rotate an API key?", top_k=3)

    assert len(docs) == 3
    doc_ids = [d.doc_id for d in docs]
    assert "rotate-api-key" in doc_ids
    for doc in docs:
        assert doc.doc_id
        assert doc.title
        assert doc.body


def test_ask_returns_grounded_sources_against_live_db(monkeypatch, live_client, mock_openai_client):
    monkeypatch.setattr("app.llm.OpenAI", lambda **kwargs: mock_openai_client)
    monkeypatch.setenv("GROQ_API_KEY", "test-integration-key")

    response = live_client.post("/ask", json={"question": "How do I rotate an API key?"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["sources"]) == 3
    for source in body["sources"]:
        assert set(source.keys()) == {"doc_id", "title"}
    source_doc_ids = {s["doc_id"] for s in body["sources"]}
    assert "rotate-api-key" in source_doc_ids
    assert body["answer"] == "Mock answer from stubbed provider."


def test_ask_emits_db_span_and_three_genai_spans_in_production(tmp_path):
    # Runs in a fresh subprocess: scripts/probe_ask_spans.py registers its
    # own observable TracerProvider before importing app.main, which is the
    # only way to see the FastAPI/SQLAlchemy spans that bind their tracers
    # at instrument time (in-process fixtures monkeypatch the provider too
    # late to observe them - see tests/test_ask.py's corrected assertion).
    output_path = tmp_path / "spans.json"
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "scripts/probe_ask_spans.py", str(output_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"probe_ask_spans.py failed (exit {result.returncode}): {result.stderr}"
    )

    data = json.loads(output_path.read_text())
    names = [s["name"] for s in data["spans"]]
    scopes = [s["scope"] for s in data["spans"]]

    assert data["http_status"] == 200

    assert names.count("rag.retrieval") == 1
    assert names.count("rag.prompt_construction") == 1
    assert names.count("chat") == 1

    retrieval_span = next(s for s in data["spans"] if s["name"] == "rag.retrieval")
    assert retrieval_span["scope"] == "app.rag"
    assert "rag.retrieval.top_k" in retrieval_span["attributes"]
    assert "rag.retrieval.doc_count" in retrieval_span["attributes"]

    prompt_span = next(s for s in data["spans"] if s["name"] == "rag.prompt_construction")
    assert prompt_span["scope"] == "app.rag"

    chat_span = next(s for s in data["spans"] if s["name"] == "chat")
    assert chat_span["scope"] == "app.llm"
    assert "gen_ai.request.model" in chat_span["attributes"]
    assert "gen_ai.usage.input_tokens" in chat_span["attributes"]

    # D-07 free DB span: SQLAlchemy names spans after the leading SQL
    # keyword, so assert on scope rather than only the name.
    assert any(
        scope == "opentelemetry.instrumentation.sqlalchemy" and name.upper().startswith("SELECT")
        for name, scope in zip(names, scopes)
    )

    assert "opentelemetry.instrumentation.fastapi" in scopes

    # Baselines measured in 02-VERIFICATION.md: 7 spans healthy-path
    # without DB instrumentation, 9 with it. Lower-bound only, so this
    # isn't brittle to connection-pool reuse.
    assert data["span_count"] >= 8
