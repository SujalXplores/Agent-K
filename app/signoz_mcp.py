"""Single call-site wrapper for every Agent K -> SigNoz MCP server query (MCP-01/02).

query_signoz(tool_name, arguments) is the ONE place `mcp.ClientSession.call_tool` is
invoked in this codebase (MCP-02). Every call opens a "signoz_mcp.query" span and
stamps a deterministic query hash (sha256 over tool_name + canonical-JSON arguments)
as a span attribute, giving Phase 5's investigation loop a ready-made signal for
loop/repeated-query detection (LAW3-02) without that logic needing to know anything
about MCP itself. Attribute names live in app/observability.py (D-06), never inline.

Connection strategy: each call opens a fresh stdio_client subprocess + ClientSession,
initializes it, calls the one tool, and tears the connection down - deliberately
simple over maintaining a long-lived reconnecting session, since Agent K's
investigation loop issues a bounded number of queries per incident (not per HTTP
request), and a hackathon build has no need for the added lifecycle complexity
(reconnect-on-drop, concurrent-call locking) of a persistent MCP connection.

The actual connect+initialize+call_tool sequence lives in _call_tool_via_mcp() as a
separate module-level function that query_signoz() is the only caller of. Kept
separate purely so tests can monkeypatch it (mirroring app/llm.py's `OpenAI`
monkeypatch pattern) - no real SigNoz MCP server or live SigNoz stack is required to
test the wrapper's span/hash contract. scripts/probe_signoz_mcp.py is the throwaway
end-to-end script (MCP-01) that DOES require a real server + live stack; running it
is a human-verification step, not covered by the offline test suite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import timedelta
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from app.observability import AGENTK_MCP_QUERY_HASH, AGENTK_MCP_TOOL_NAME

logger = logging.getLogger(__name__)

DEFAULT_MCP_COMMAND = "./signoz-mcp-server"
MCP_QUERY_TIMEOUT_S = 30.0


def compute_query_hash(tool_name: str, arguments: dict[str, Any]) -> str:
    """Deterministic sha256 hex digest over (tool_name, arguments).

    Canonicalizes `arguments` via json.dumps(..., sort_keys=True) so key order never
    changes the hash - two calls with the same tool_name and equal (possibly
    differently-ordered) arguments always hash identically, which is exactly the
    property a repeated-query watchdog needs.
    """
    canonical = json.dumps(arguments, sort_keys=True, default=str)
    digest_input = f"{tool_name}:{canonical}".encode()
    return hashlib.sha256(digest_input).hexdigest()


async def _call_tool_via_mcp(tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Open a fresh MCP stdio connection, initialize, call one tool, tear down.

    Reads SIGNOZ_MCP_COMMAND (default DEFAULT_MCP_COMMAND) and passes SIGNOZ_URL /
    SIGNOZ_API_KEY through to the subprocess's environment, per the locked
    stdio_client(StdioServerParameters(command=..., env={...})) client pattern.
    Never called anywhere except query_signoz() - kept as a separate function
    purely so tests can monkeypatch it without a real server.
    """
    load_dotenv()
    command = os.getenv("SIGNOZ_MCP_COMMAND", DEFAULT_MCP_COMMAND)
    server_params = StdioServerParameters(
        command=command,
        env={
            "SIGNOZ_URL": os.getenv("SIGNOZ_URL", ""),
            "SIGNOZ_API_KEY": os.getenv("SIGNOZ_API_KEY", ""),
        },
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(
                tool_name,
                arguments,
                read_timeout_seconds=timedelta(seconds=MCP_QUERY_TIMEOUT_S),
            )


async def query_signoz(tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
    """The single call-site every SigNoz evidence query MUST go through (MCP-02).

    Opens one "signoz_mcp.query" span per call, stamps AGENTK_MCP_TOOL_NAME and
    AGENTK_MCP_QUERY_HASH on it before the call so both attributes are present
    regardless of outcome, marks the span ERROR (without swallowing the exception)
    on a connection/transport failure or a tool-reported error result, and never
    logs the raw evidence payload - only the tool name and hash (content-safety,
    mirrors app/observability.py's discipline: evidence content can be large and
    is not this function's business to persist or print).
    """
    query_hash = compute_query_hash(tool_name, arguments)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("signoz_mcp.query") as span:
        span.set_attribute(AGENTK_MCP_TOOL_NAME, tool_name)
        span.set_attribute(AGENTK_MCP_QUERY_HASH, query_hash)
        try:
            result = await _call_tool_via_mcp(tool_name, arguments)
        except Exception:
            span.set_status(StatusCode.ERROR)
            logger.error(
                "signoz mcp query failed: tool=%s hash=%s", tool_name, query_hash
            )
            raise

        if result.isError:
            span.set_status(StatusCode.ERROR)

        logger.info("signoz mcp query complete: tool=%s hash=%s", tool_name, query_hash)
        return result
