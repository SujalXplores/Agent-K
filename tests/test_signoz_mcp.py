"""Tests for app.signoz_mcp's single SigNoz MCP query-wrapper call site (MCP-01/02).

_call_tool_via_mcp (the actual stdio_client/ClientSession connection) is
monkeypatched throughout - no real SigNoz MCP server or live stack is required.
These tests prove the wrapper contract: exactly one span per call, a deterministic
query hash stamped on it regardless of outcome, and ERROR status on both
transport failures and tool-reported errors (without swallowing exceptions).
"""

from __future__ import annotations

import pytest
from mcp.types import CallToolResult, TextContent

from app import signoz_mcp
from app.observability import AGENTK_MCP_QUERY_HASH, AGENTK_MCP_TOOL_NAME


def _query_spans(exporter):
    return [s for s in exporter.get_finished_spans() if s.name == "signoz_mcp.query"]


# --- compute_query_hash ---


def test_hash_deterministic_regardless_of_key_order():
    h1 = signoz_mcp.compute_query_hash("get_trace", {"a": 1, "b": 2})
    h2 = signoz_mcp.compute_query_hash("get_trace", {"b": 2, "a": 1})
    assert h1 == h2


def test_hash_differs_for_different_tool_name():
    h1 = signoz_mcp.compute_query_hash("get_trace", {"id": "abc"})
    h2 = signoz_mcp.compute_query_hash("get_logs", {"id": "abc"})
    assert h1 != h2


def test_hash_differs_for_different_arguments():
    h1 = signoz_mcp.compute_query_hash("get_trace", {"id": "abc"})
    h2 = signoz_mcp.compute_query_hash("get_trace", {"id": "xyz"})
    assert h1 != h2


# --- query_signoz: success path ---


@pytest.mark.asyncio
async def test_query_signoz_emits_exactly_one_span_with_tool_and_hash(
    monkeypatch, in_memory_exporter
):
    call_count = 0

    async def fake_call(tool_name, arguments):
        nonlocal call_count
        call_count += 1
        return CallToolResult(content=[TextContent(type="text", text="ok")], isError=False)

    monkeypatch.setattr(signoz_mcp, "_call_tool_via_mcp", fake_call)

    result = await signoz_mcp.query_signoz("get_trace", {"trace_id": "t-1"})

    assert call_count == 1  # single call-site, called exactly once
    assert result.isError is False

    spans = _query_spans(in_memory_exporter)
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs[AGENTK_MCP_TOOL_NAME] == "get_trace"
    assert attrs[AGENTK_MCP_QUERY_HASH] == signoz_mcp.compute_query_hash(
        "get_trace", {"trace_id": "t-1"}
    )
    assert spans[0].status.status_code.name != "ERROR"


@pytest.mark.asyncio
async def test_query_signoz_passes_arguments_through_unchanged(monkeypatch, in_memory_exporter):
    captured = {}

    async def fake_call(tool_name, arguments):
        captured["tool_name"] = tool_name
        captured["arguments"] = arguments
        return CallToolResult(content=[], isError=False)

    monkeypatch.setattr(signoz_mcp, "_call_tool_via_mcp", fake_call)

    await signoz_mcp.query_signoz("get_logs", {"service": "rag", "limit": 5})

    assert captured == {"tool_name": "get_logs", "arguments": {"service": "rag", "limit": 5}}


# --- query_signoz: tool-reported error (isError=True) ---


@pytest.mark.asyncio
async def test_query_signoz_marks_span_error_on_tool_reported_error(
    monkeypatch, in_memory_exporter
):
    async def fake_call(tool_name, arguments):
        return CallToolResult(content=[], isError=True)

    monkeypatch.setattr(signoz_mcp, "_call_tool_via_mcp", fake_call)

    result = await signoz_mcp.query_signoz("get_metric", {"name": "does_not_exist"})

    assert result.isError is True  # not raised - caller decides what to do
    spans = _query_spans(in_memory_exporter)
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"
    # hash/tool-name still stamped even on a tool-reported error
    assert spans[0].attributes[AGENTK_MCP_TOOL_NAME] == "get_metric"


# --- query_signoz: transport/connection failure ---


@pytest.mark.asyncio
async def test_query_signoz_marks_span_error_and_reraises_on_transport_failure(
    monkeypatch, in_memory_exporter
):
    async def fake_call(tool_name, arguments):
        raise ConnectionError("mcp server unreachable")

    monkeypatch.setattr(signoz_mcp, "_call_tool_via_mcp", fake_call)

    with pytest.raises(ConnectionError):
        await signoz_mcp.query_signoz("get_trace", {"trace_id": "t-2"})

    spans = _query_spans(in_memory_exporter)
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"
    assert spans[0].attributes[AGENTK_MCP_TOOL_NAME] == "get_trace"
    assert spans[0].attributes[AGENTK_MCP_QUERY_HASH] == signoz_mcp.compute_query_hash(
        "get_trace", {"trace_id": "t-2"}
    )


# --- server-process configuration (SIGNOZ_MCP_COMMAND / SIGNOZ_MCP_ARGS) ---


def _captured_params(monkeypatch):
    """Run _call_tool_via_mcp far enough to capture the StdioServerParameters it
    builds, without launching a subprocess."""
    captured = {}

    def fake_stdio_client(params):
        captured["params"] = params
        raise RuntimeError("stop here - we only wanted the params")

    monkeypatch.setattr(signoz_mcp, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(signoz_mcp, "stdio_client", fake_stdio_client)
    return captured


@pytest.mark.asyncio
async def test_empty_command_env_falls_back_to_the_real_binary(monkeypatch):
    """docker-compose's ${VAR:-} sets an EMPTY STRING, not an unset variable.

    A getenv default would hand StdioServerParameters "" and try to exec nothing.
    The fallback must treat empty as absent, or a stack that simply didn't
    configure an MCP server would fail in a confusing place.
    """
    monkeypatch.setenv("SIGNOZ_MCP_COMMAND", "")
    monkeypatch.setenv("SIGNOZ_MCP_ARGS", "")
    captured = _captured_params(monkeypatch)

    with pytest.raises(RuntimeError):
        await signoz_mcp._call_tool_via_mcp("t", {})

    assert captured["params"].command == signoz_mcp.DEFAULT_MCP_COMMAND
    assert captured["params"].args == []


@pytest.mark.asyncio
async def test_command_and_args_are_read_from_env(monkeypatch):
    """A server that isn't a self-contained executable needs argv."""
    monkeypatch.setenv("SIGNOZ_MCP_COMMAND", "python")
    monkeypatch.setenv("SIGNOZ_MCP_ARGS", "/srv/scripts/demo_mcp_server.py --verbose")
    captured = _captured_params(monkeypatch)

    with pytest.raises(RuntimeError):
        await signoz_mcp._call_tool_via_mcp("t", {})

    assert captured["params"].command == "python"
    assert captured["params"].args == ["/srv/scripts/demo_mcp_server.py", "--verbose"]


@pytest.mark.asyncio
async def test_quoted_arg_paths_survive_splitting(monkeypatch):
    """shlex.split, not str.split - a path with a space must stay one argv entry."""
    monkeypatch.setenv("SIGNOZ_MCP_COMMAND", "python")
    monkeypatch.setenv("SIGNOZ_MCP_ARGS", '"/opt/my server/fixture.py"')
    captured = _captured_params(monkeypatch)

    with pytest.raises(RuntimeError):
        await signoz_mcp._call_tool_via_mcp("t", {})

    assert captured["params"].args == ["/opt/my server/fixture.py"]
