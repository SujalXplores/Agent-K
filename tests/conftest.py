"""Shared pytest fixtures for offline (mocked) app.llm tests.

Extended later by 02-04 for retrieval/rag tests.
"""

from unittest.mock import MagicMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


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
