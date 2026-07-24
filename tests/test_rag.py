"""Offline (mocked, no DB, no network) tests for app.rag's retrieve/build_prompt.

Covers D-07 (rag.retrieval + rag.prompt_construction are two of the three
D-07 GenAI-instrumented spans), D-06 (span attributes read from the shared
app.observability constants, not retyped literals), and D-03/D-05 (fixed
top_k retrieval + the grounded prompt that delegates "I don't know" behavior
to the LLM rather than a refusal code branch).
"""

import pytest

import app.rag as rag_module
from app.observability import RAG_RETRIEVAL_DOC_COUNT, RAG_RETRIEVAL_TOP_K


@pytest.mark.asyncio
async def test_retrieve_opens_span_with_top_k_and_doc_count_attributes(
    monkeypatch, in_memory_exporter, fake_session, stub_documents
):
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)

    await rag_module.retrieve(fake_session, "How do I rotate my API key?", top_k=3)

    spans = in_memory_exporter.get_finished_spans()
    retrieval_spans = [s for s in spans if s.name == "rag.retrieval"]
    assert len(retrieval_spans) == 1

    attrs = retrieval_spans[0].attributes
    assert attrs[RAG_RETRIEVAL_TOP_K] == 3
    assert attrs[RAG_RETRIEVAL_DOC_COUNT] == len(stub_documents)


@pytest.mark.asyncio
async def test_retrieve_honors_top_k_ordering_and_limit(
    monkeypatch, fake_session, stub_documents
):
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)

    docs = await rag_module.retrieve(fake_session, "How do I rotate my API key?", top_k=3)

    # The mocked session hands back exactly what it's configured with; the
    # real ordering/limit enforcement happens in the SQL statement built by
    # retrieve() and executed against the live DB, so assert the *statement*
    # itself was built with the limit and an ORDER BY clause, not just that
    # the mock returned rows (which it always would regardless).
    assert docs == stub_documents
    fake_session.execute.assert_awaited_once()
    stmt = fake_session.execute.await_args.args[0]
    assert stmt._limit_clause is not None
    assert len(stmt._order_by_clauses) > 0


@pytest.mark.asyncio
async def test_retrieve_default_top_k_is_three(monkeypatch, fake_session):
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)

    await rag_module.retrieve(fake_session, "How do I rotate my API key?")

    stmt = fake_session.execute.await_args.args[0]
    assert stmt._limit_clause.value == 3


def test_build_prompt_opens_span_and_returns_grounded_system_prompt(
    in_memory_exporter, stub_documents
):
    system, user = rag_module.build_prompt("How do I rotate my API key?", stub_documents)

    spans = in_memory_exporter.get_finished_spans()
    prompt_spans = [s for s in spans if s.name == "rag.prompt_construction"]
    assert len(prompt_spans) == 1

    assert "ONLY" in system
    assert "do not know" in system.lower() or "don't know" in system.lower()
    assert "How do I rotate my API key?" in user
    for doc in stub_documents:
        assert doc.body in user


def test_build_prompt_with_empty_docs_still_grounds_dont_know(in_memory_exporter):
    system, user = rag_module.build_prompt("What's the meaning of life?", [])

    # Grounding is delegated entirely to the system prompt (D-03) - no
    # separate refusal branch - so the same system prompt must apply
    # regardless of whether any docs were retrieved.
    assert "do not know" in system.lower() or "don't know" in system.lower()
    assert "What's the meaning of life?" in user
