"""Injection tests for the two remaining fault scenarios: retry-storm (FLAG-03,
app/llm.py) and DB-pool-exhaustion (FLAG-05, app/db.py).

Retry-storm's signal is a COST/CALL-RATE anomaly - the request must stay a
200-equivalent (returns an LlmResult) on eventual success while the chat span's
retry_count spikes. DB-pool-exhaustion uses an application-level semaphore so a
concurrent checkout fails without touching the real engine/pool. The reset_flags
autouse fixture keeps each test isolated.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import app.db as db_module
import app.llm as llm_module
from app import flags


@pytest.fixture(autouse=True)
def _groq_key(monkeypatch):
    """Every generate() call constructs a client; give it a dummy key + mocked SDK."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")


def _stub_completion():
    usage = MagicMock(input_tokens=7, output_tokens=13)
    message = MagicMock(content="Mock answer from stubbed provider.")
    choice = MagicMock(message=message)
    return MagicMock(model="llama-3.1-8b-instant", usage=usage, choices=[choice])


def _chat_span(exporter):
    spans = [s for s in exporter.get_finished_spans() if s.name == "chat"]
    assert len(spans) == 1
    return spans[0]


# --- FLAG-03 retry storm ---


def test_retry_storm_off_single_attempt(monkeypatch, in_memory_exporter):
    client = MagicMock()
    client.chat.completions.create.return_value = _stub_completion()
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: client)

    assert flags.is_enabled("retry_storm") is False
    result = llm_module.generate("q?")

    assert result.answer == "Mock answer from stubbed provider."
    assert client.chat.completions.create.call_count == 1
    assert _chat_span(in_memory_exporter).attributes["agentk.llm.retry_count"] == 1
    # normal timeout used when OFF
    assert client.chat.completions.create.call_args.kwargs["timeout"] == llm_module.NORMAL_TIMEOUT_S


def test_retry_storm_on_retries_then_succeeds(monkeypatch, in_memory_exporter):
    client = MagicMock()
    # raise twice, then succeed on the third attempt
    client.chat.completions.create.side_effect = [
        RuntimeError("transient 1"),
        RuntimeError("transient 2"),
        _stub_completion(),
    ]
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: client)

    flags.set_flag("retry_storm", True)
    result = llm_module.generate("q?")

    # HTTP-200-equivalent: returns an LlmResult despite the transient failures
    assert result.answer == "Mock answer from stubbed provider."
    assert client.chat.completions.create.call_count == 3
    assert _chat_span(in_memory_exporter).attributes["agentk.llm.retry_count"] == 3
    # lowered timeout used on retry-storm attempts
    assert (
        client.chat.completions.create.call_args.kwargs["timeout"]
        == llm_module.RETRY_STORM_TIMEOUT_S
    )


def test_retry_storm_on_exhaustion_propagates(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("always fails")
    monkeypatch.setattr(llm_module, "OpenAI", lambda **kwargs: client)

    flags.set_flag("retry_storm", True)
    with pytest.raises(RuntimeError):
        llm_module.generate("q?")

    assert client.chat.completions.create.call_count == llm_module.MAX_RETRIES


# --- FLAG-05 DB pool exhaustion ---


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def _fake_sessionmaker(monkeypatch):
    monkeypatch.setattr(db_module, "AsyncSessionLocal", lambda: _FakeSession())


@pytest.mark.asyncio
async def test_pool_exhaustion_off_concurrent_checkouts_succeed(_fake_sessionmaker):
    assert flags.is_enabled("db_pool_exhaustion") is False

    async def _checkout():
        gen = db_module.get_session()
        session = await gen.__anext__()
        await gen.aclose()
        return session

    import asyncio

    a, b = await asyncio.gather(_checkout(), _checkout())
    assert isinstance(a, _FakeSession)
    assert isinstance(b, _FakeSession)


@pytest.mark.asyncio
async def test_pool_exhaustion_on_second_checkout_times_out(_fake_sessionmaker, caplog):
    flags.set_flag("db_pool_exhaustion", True)

    # Hold the first checkout open (acquires the semaphore, suspended at yield).
    gen1 = db_module.get_session()
    session1 = await gen1.__anext__()
    assert isinstance(session1, _FakeSession)

    # A concurrent second checkout cannot acquire and must raise a
    # pool-exhaustion-shaped TimeoutError, logged at error level.
    gen2 = db_module.get_session()
    with caplog.at_level("ERROR"):
        with pytest.raises(TimeoutError, match="pool exhaustion"):
            await gen2.__anext__()

    assert any("pool exhaustion" in r.message for r in caplog.records)

    # Releasing the first checkout frees the semaphore for later tests.
    await gen1.aclose()
