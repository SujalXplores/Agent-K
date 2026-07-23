"""Tests for OpenTelemetry instrumentation and GenAI span attributes."""

from __future__ import annotations

from app.otel import genai_span_attrs


# ─── genai_span_attrs helper ──────────────────────────────────────────


def test_genai_span_attrs_minimal():
    """Only non-None values should be included."""
    attrs = genai_span_attrs(model="llama-3.1-8b-instant")
    assert attrs == {"gen_ai.request.model": "llama-3.1-8b-instant"}


def test_genai_span_attrs_all_fields():
    """All standard GenAI attributes should be set correctly."""
    attrs = genai_span_attrs(
        model="llama-3.3-70b-versatile",
        operation="chat.completion",
        provider="groq",
        input_tokens=150,
        output_tokens=80,
        finish_reasons=["stop"],
    )
    assert attrs["gen_ai.request.model"] == "llama-3.3-70b-versatile"
    assert attrs["gen_ai.operation.name"] == "chat.completion"
    assert attrs["gen_ai.provider.name"] == "groq"
    assert attrs["gen_ai.usage.input_tokens"] == 150
    assert attrs["gen_ai.usage.output_tokens"] == 80
    assert attrs["gen_ai.response.finish_reasons"] == ["stop"]


def test_genai_span_attrs_none_values_excluded():
    """None values should not appear in the attributes dict."""
    attrs = genai_span_attrs(
        model="llama-3.1-8b-instant",
        operation=None,
        provider="groq",
        input_tokens=None,
    )
    assert "gen_ai.operation.name" not in attrs
    assert "gen_ai.usage.input_tokens" not in attrs
    assert attrs["gen_ai.request.model"] == "llama-3.1-8b-instant"
    assert attrs["gen_ai.provider.name"] == "groq"


def test_genai_span_attrs_extra_keys():
    """Extra keys should be prefixed with gen_ai. if not already namespaced."""
    attrs = genai_span_attrs(
        model="test-model",
        custom_field="value",
        already_namespaced="kept_as_is",
    )
    assert attrs["gen_ai.custom_field"] == "value"
    assert attrs["gen_ai.already_namespaced"] == "kept_as_is"


def test_genai_span_attrs_empty():
    """No arguments should produce an empty dict."""
    attrs = genai_span_attrs()
    assert attrs == {}


# ─── OTel initialization ──────────────────────────────────────────────


def test_otel_init_console_exporter(monkeypatch):
    """init_otel should work with the console exporter (default)."""
    from app.otel import init_otel

    # Force console exporter
    monkeypatch.setenv("OTEL_EXPORTER", "console")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "test-service")

    # Clear the cached settings so the env var takes effect
    from app.config import get_settings

    get_settings.cache_clear()

    init_otel()  # Should not raise

    from app.otel import get_tracer, get_meter

    tracer = get_tracer()
    meter = get_meter()
    assert tracer is not None
    assert meter is not None

    # Clean up
    get_settings.cache_clear()
