"""Shared pytest fixtures for offline (mocked) app.llm / app.rag / /ask tests.

Extended in 02-04 with retrieval fixtures (stub_documents, fake_session) and
a FastAPI TestClient fixture (client) with get_session overridden, so
tests/test_rag.py and tests/test_ask.py never touch a real database.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def pytest_configure(config):
    """Register the `integration` marker for tests that require the live
    rag-postgres container seeded by scripts/seed_corpus.py."""
    config.addinivalue_line(
        "markers",
        "integration: requires the live rag-postgres container seeded by "
        "scripts/seed_corpus.py (see tests/test_integration_rag.py)",
    )


@pytest.fixture(autouse=True)
def reset_flags():
    """Reset every failure-injection flag to OFF after each test.

    app.flags._flags is module-level global state that would otherwise leak a
    toggled-on scenario from one test into every later test in the process. This
    autouse fixture guarantees each test starts (and the next one resumes) from
    the all-OFF default, matching the process-start posture. Imported lazily so
    tests that never touch app.flags still load conftest without importing it.
    """
    yield
    from app import flags

    for name in flags.FLAG_NAMES:
        flags.set_flag(name, False)


@pytest.fixture
def in_memory_exporter(monkeypatch):
    """Wire an InMemorySpanExporter as the active global tracer provider.

    opentelemetry.trace.set_tracer_provider() is a do-once operation per
    process - the SDK blocks re-registration after the first real call and
    only logs a warning on subsequent attempts, which would leak the first
    test's provider into every later test. Instead, monkeypatch the
    module-level `_TRACER_PROVIDER` global directly; monkeypatch restores it
    automatically after each test, giving full per-test isolation. This only
    works because app/llm.py acquires its tracer fresh inside generate() via
    trace.get_tracer(__name__) on every call rather than caching one at
    import time.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(trace, "_TRACER_PROVIDER", provider)
    yield exporter


@pytest.fixture
def mock_openai_client():
    """A MagicMock standing in for an openai.OpenAI client instance.

    .chat.completions.create(...) returns a stub completion exposing
    choices[0].message.content, .model, and .usage.input_tokens/output_tokens
    - the shape app.llm.generate() reads from a response, no real network
    call or API key required.
    """
    usage = MagicMock(input_tokens=7, output_tokens=13)
    message = MagicMock(content="Mock answer from stubbed provider.")
    choice = MagicMock(message=message)
    completion = MagicMock(model="llama-3.1-8b-instant", usage=usage, choices=[choice])

    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


@pytest.fixture
def stub_documents():
    """Three stub Document-like rows standing in for a real pgvector result.

    Plain MagicMocks (not real ORM instances) exposing exactly the
    attributes app/rag.py and the /ask handler read: doc_id, title, body.
    """

    def _doc(doc_id: str, title: str, body: str):
        stub = MagicMock()
        stub.doc_id = doc_id
        stub.title = title
        stub.body = body
        return stub

    return [
        _doc(
            "doc-billing-01",
            "Updating Your Billing Address",
            "To update your billing address, go to Settings > Billing and edit "
            "the address on file. Changes apply to your next invoice.",
        ),
        _doc(
            "doc-auth-02",
            "Rotating API Keys",
            "You can rotate an API key from the Developer console under API Keys. "
            "Rotating a key immediately invalidates the previous one.",
        ),
        _doc(
            "doc-security-03",
            "Managing Team Permissions",
            "Admins can manage per-seat permissions under Security > Team Roles.",
        ),
    ]


@pytest.fixture
def fake_session(stub_documents):
    """A fake AsyncSession whose execute() resolves to stub_documents.

    Mirrors the real AsyncSession.execute(stmt) -> result.scalars().all()
    shape used by app/rag.py's retrieve(), with no real DB connection.
    """
    scalars_result = MagicMock()
    scalars_result.all.return_value = stub_documents
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_result

    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    return session


@pytest.fixture
def client(fake_session):
    """FastAPI TestClient with app.db.get_session overridden to a fake session.

    Imports app.main lazily (inside the fixture body, not at module import
    time) so tests that only need app.rag/app.llm fixtures above never pay
    the cost of importing the full app (and its setup_telemetry() call).
    """
    from app.db import get_session
    from app.main import app as fastapi_app

    async def _override_get_session():
        yield fake_session

    fastapi_app.dependency_overrides[get_session] = _override_get_session
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
