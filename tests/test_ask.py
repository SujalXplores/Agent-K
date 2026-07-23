"""Offline (mocked, no DB, no network, no API key) tests for POST /ask.

Covers D-04 (response contract), RAG-03/D-07 (exactly three GenAI-
instrumented spans per call: rag.retrieval, rag.prompt_construction, chat),
and input-bounds validation (T-02-INPUT/T-02-DoS).
"""

import app.llm as llm_module
import app.rag as rag_module


def _wire_offline(monkeypatch, mock_openai_client):
    """Monkeypatch embed_text + the OpenAI client so /ask never hits the
    network or a real DB - shared setup for every test in this module."""
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: mock_openai_client)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")


def test_ask_returns_answer_and_sources_matching_d04_contract(
    monkeypatch, client, mock_openai_client, stub_documents
):
    _wire_offline(monkeypatch, mock_openai_client)

    response = client.post("/ask", json={"question": "How do I rotate my API key?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Mock answer from stubbed provider."
    assert body["sources"] == [
        {"doc_id": doc.doc_id, "title": doc.title} for doc in stub_documents
    ]


def test_ask_produces_exactly_three_genai_spans(
    monkeypatch, client, in_memory_exporter, mock_openai_client
):
    _wire_offline(monkeypatch, mock_openai_client)

    response = client.post("/ask", json={"question": "How do I rotate my API key?"})
    assert response.status_code == 200

    spans = in_memory_exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    assert span_names.count("rag.retrieval") == 1
    assert span_names.count("rag.prompt_construction") == 1
    assert span_names.count("chat") == 1
    assert len(spans) == 3

    retrieval_span = next(s for s in spans if s.name == "rag.retrieval")
    prompt_span = next(s for s in spans if s.name == "rag.prompt_construction")
    chat_span = next(s for s in spans if s.name == "chat")

    assert "rag.retrieval.top_k" in retrieval_span.attributes
    assert "rag.retrieval.doc_count" in retrieval_span.attributes
    assert "rag.prompt_construction.doc_count" in prompt_span.attributes
    assert "gen_ai.request.model" in chat_span.attributes
    assert "gen_ai.usage.input_tokens" in chat_span.attributes


def test_ask_missing_question_returns_422(client):
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_empty_question_returns_422(client):
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 422


def test_ask_oversized_question_returns_422(client):
    response = client.post("/ask", json={"question": "x" * 2001})
    assert response.status_code == 422


def test_ask_sources_correspond_to_retrieved_docs(
    monkeypatch, client, mock_openai_client, stub_documents
):
    _wire_offline(monkeypatch, mock_openai_client)

    response = client.post("/ask", json={"question": "How do I rotate my API key?"})
    body = response.json()

    returned_doc_ids = {s["doc_id"] for s in body["sources"]}
    expected_doc_ids = {doc.doc_id for doc in stub_documents}
    assert returned_doc_ids == expected_doc_ids
    for source in body["sources"]:
        assert set(source.keys()) == {"doc_id", "title"}
