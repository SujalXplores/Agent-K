"""Injection tests for the two retrieval-tier fault scenarios in app.rag:
prompt-regression (FLAG-02) and retrieval-latency (FLAG-04).

Both prove the injected symptom changes the EMITTED span attributes (via
in_memory_exporter), not just the return value - a broken prompt still returns
HTTP 200, so the queryable regression_active / latency_injected attributes are
the concrete signals SigNoz filters on. The reset_flags autouse fixture keeps
each test isolated.
"""

from __future__ import annotations

import pytest

import app.rag as rag_module
from app import flags
from app.observability import (
    RAG_PROMPT_REGRESSION_ACTIVE,
    RAG_RETRIEVAL_LATENCY_INJECTED,
)


def _prompt_span(exporter):
    spans = [s for s in exporter.get_finished_spans() if s.name == "rag.prompt_construction"]
    assert len(spans) == 1
    return spans[0]


def _retrieval_span(exporter):
    spans = [s for s in exporter.get_finished_spans() if s.name == "rag.retrieval"]
    assert len(spans) == 1
    return spans[0]


# --- FLAG-02 prompt regression ---


def test_prompt_regression_off_uses_grounded_prompt(in_memory_exporter, stub_documents):
    assert flags.is_enabled("prompt_regression") is False
    system, user = rag_module.build_prompt("How do I rotate my API key?", stub_documents)

    assert system == rag_module.SYSTEM_PROMPT
    assert _prompt_span(in_memory_exporter).attributes[RAG_PROMPT_REGRESSION_ACTIVE] is False


def test_prompt_regression_on_swaps_prompt_and_stamps_attribute(
    in_memory_exporter, stub_documents
):
    flags.set_flag("prompt_regression", True)
    system, user = rag_module.build_prompt("How do I rotate my API key?", stub_documents)

    assert system == rag_module.BROKEN_SYSTEM_PROMPT
    assert rag_module.BROKEN_SYSTEM_PROMPT != rag_module.SYSTEM_PROMPT
    assert _prompt_span(in_memory_exporter).attributes[RAG_PROMPT_REGRESSION_ACTIVE] is True


def test_prompt_regression_leaves_user_prompt_unchanged(stub_documents):
    # Only the system prompt swaps; the user prompt / context assembly is
    # byte-for-byte identical between flag states.
    _, user_off = rag_module.build_prompt("q?", stub_documents)
    flags.set_flag("prompt_regression", True)
    _, user_on = rag_module.build_prompt("q?", stub_documents)
    assert user_off == user_on


# --- FLAG-04 retrieval latency ---


@pytest.mark.asyncio
async def test_retrieval_latency_off_no_delay(
    monkeypatch, in_memory_exporter, fake_session
):
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)
    assert flags.is_enabled("retrieval_latency") is False

    await rag_module.retrieve(fake_session, "How do I rotate my API key?")

    assert _retrieval_span(in_memory_exporter).attributes[RAG_RETRIEVAL_LATENCY_INJECTED] is False


@pytest.mark.asyncio
async def test_retrieval_latency_on_delays_and_stamps_attribute(
    monkeypatch, in_memory_exporter, fake_session
):
    monkeypatch.setattr(rag_module, "embed_text", lambda query: [0.1] * 384)
    # Keep the test fast: shrink the injected delay to a tiny value and record
    # that asyncio.sleep was actually awaited with it.
    monkeypatch.setattr(rag_module, "RETRIEVAL_LATENCY_INJECT_S", 0.01)
    slept: list[float] = []

    import asyncio as _asyncio

    real_sleep = _asyncio.sleep

    async def _record_sleep(seconds):
        slept.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(rag_module.asyncio, "sleep", _record_sleep)

    flags.set_flag("retrieval_latency", True)
    await rag_module.retrieve(fake_session, "How do I rotate my API key?")

    assert slept == [0.01]
    assert _retrieval_span(in_memory_exporter).attributes[RAG_RETRIEVAL_LATENCY_INJECTED] is True
