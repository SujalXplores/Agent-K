"""Offline (mocked, no network) tests for app.llm's provider factory + generate().

Covers RAG-04 (env-var-only provider switching) and RAG-03/D-06 (generation
span carries stable gen_ai.* attributes via the shared observability helper).
"""

from unittest.mock import MagicMock

import pytest

import app.llm as llm_module


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    """Ensure no test leaks provider/env state into another."""
    for var in ("LLM_PROVIDER", "GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_get_client_defaults_to_groq(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr(llm_module, "OpenAI", fake_openai)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    llm_module.get_client()

    assert captured["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["api_key"] == "test-groq-key"


@pytest.mark.parametrize(
    "provider,expected_base_url,api_key_var",
    [
        ("cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
        (
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            "GEMINI_API_KEY",
        ),
    ],
)
def test_get_client_switches_provider_via_env_var_only(
    monkeypatch, provider, expected_base_url, api_key_var
):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr(llm_module, "OpenAI", fake_openai)
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(api_key_var, "test-key")

    llm_module.get_client()

    assert captured["base_url"] == expected_base_url


def test_get_client_reads_api_key_from_matching_provider_env_var(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr(llm_module, "OpenAI", fake_openai)
    monkeypatch.setenv("LLM_PROVIDER", "cerebras")
    monkeypatch.setenv("CEREBRAS_API_KEY", "cerebras-secret")

    llm_module.get_client()

    assert captured["api_key"] == "cerebras-secret"


def test_get_client_rejects_unknown_provider(monkeypatch):
    """T-02-04: an unrecognized LLM_PROVIDER must fail fast, not silently mis-route."""
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")

    with pytest.raises(KeyError):
        llm_module.get_client()


def test_generate_emits_one_chat_span_with_gen_ai_attributes(
    monkeypatch, in_memory_exporter, mock_openai_client
):
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: mock_openai_client)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    llm_module.generate("What is the refund policy?")

    spans = in_memory_exporter.get_finished_spans()
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) == 1

    attrs = chat_spans[0].attributes
    assert attrs["gen_ai.request.model"] == "llama-3.1-8b-instant"
    assert attrs["gen_ai.usage.input_tokens"] == 7
    assert attrs["gen_ai.usage.output_tokens"] == 13


def test_generate_returns_assistant_message_text(monkeypatch, mock_openai_client):
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: mock_openai_client)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    result = llm_module.generate("What is the refund policy?")

    assert result.answer == "Mock answer from stubbed provider."


def test_get_client_raises_when_provider_key_missing_and_never_falls_back_to_openai_key(
    monkeypatch,
):
    """CR-04: a missing provider key must never let the SDK read OPENAI_API_KEY."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unrelated-sentinel")

    called = {"constructed": False}

    def fake_openai(**kwargs):
        called["constructed"] = True
        return MagicMock()

    monkeypatch.setattr(llm_module, "OpenAI", fake_openai)

    with pytest.raises(llm_module.MissingProviderKeyError) as excinfo:
        llm_module.get_client()

    assert called["constructed"] is False
    assert "sk-unrelated-sentinel" not in str(excinfo.value)


def test_get_client_raises_when_provider_key_is_empty_string(monkeypatch):
    """CR-04: .env.example's GROQ_API_KEY= (empty string) must also fail fast."""
    monkeypatch.setenv("GROQ_API_KEY", "")

    with pytest.raises(llm_module.MissingProviderKeyError):
        llm_module.get_client()


def test_generate_raises_typed_error_and_marks_chat_span_error_when_no_choices(
    monkeypatch, in_memory_exporter
):
    """CR-03: an empty choices list must raise a typed error, not IndexError."""
    empty_completion = MagicMock(
        model="llama-3.1-8b-instant",
        usage=MagicMock(input_tokens=5, output_tokens=0),
        choices=[],
    )
    client = MagicMock()
    client.chat.completions.create.return_value = empty_completion

    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: client)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    with pytest.raises(llm_module.EmptyCompletionError):
        llm_module.generate("What is the refund policy?")

    spans = in_memory_exporter.get_finished_spans()
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) == 1
    assert chat_spans[0].status.status_code.name == "ERROR"
    assert "gen_ai.request.model" in chat_spans[0].attributes


def test_generate_returns_empty_string_when_message_content_is_none(monkeypatch):
    """CR-03: a None message.content must not violate the D-04 str contract."""
    message = MagicMock(content=None)
    choice = MagicMock(message=message)
    completion = MagicMock(
        model="llama-3.1-8b-instant",
        usage=MagicMock(input_tokens=5, output_tokens=0),
        choices=[choice],
    )
    client = MagicMock()
    client.chat.completions.create.return_value = completion

    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: client)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    result = llm_module.generate("What is the refund policy?")

    assert result.answer == ""
