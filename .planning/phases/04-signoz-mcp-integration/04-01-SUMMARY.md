---
phase: 04-signoz-mcp-integration
plan: 01
status: complete
requirements-completed: [MCP-01, MCP-02]  # MCP-01's live/not-mocked half is human-verification (no SigNoz MCP server/stack in this environment)
key-files:
  created:
    - app/signoz_mcp.py
    - tests/test_signoz_mcp.py
    - scripts/probe_signoz_mcp.py
  modified:
    - requirements.txt
    - .env.example
    - app/observability.py
completed: 2026-07-24
---

# Phase 4 Plan 01: SigNoz MCP Query Wrapper

**Built `query_signoz(tool_name, arguments)` — the single call-site every SigNoz MCP query
must go through (MCP-02). It opens one `signoz_mcp.query` span per call and stamps a
deterministic query hash on it, giving Phase 5's investigation loop a ready-made
loop/repeated-query detection signal (LAW3-02) with zero MCP-specific knowledge required
on its side.**

## Research (done directly, no gsd)

Verified the real `mcp==1.28.1` SDK API by installing it and introspecting signatures
directly (not from memory): `StdioServerParameters(command, args, env, ...)`,
`stdio_client(server_params)` (async context manager → read/write streams),
`ClientSession(read_stream, write_stream)` (async context manager), `session.initialize()`,
`session.call_tool(name, arguments, read_timeout_seconds=...) -> CallToolResult`
(`content`, `structuredContent`, `isError`, `meta`). Confirmed `Span.set_status` accepts a
bare `StatusCode` directly (no `Status(...)` wrapper needed).

## Accomplishments

- `app/signoz_mcp.py`:
  - `compute_query_hash(tool_name, arguments)` — sha256 over `tool_name` + canonical
    (`sort_keys=True`) JSON of `arguments`; deterministic regardless of key order.
  - `_call_tool_via_mcp(tool_name, arguments)` — the actual connect/initialize/call_tool
    sequence (fresh `stdio_client` subprocess + `ClientSession` per call, torn down after);
    reads `SIGNOZ_MCP_COMMAND` and passes `SIGNOZ_URL`/`SIGNOZ_API_KEY` to the subprocess
    env, per the locked client pattern. Kept as a separate module-level function purely so
    tests can monkeypatch it (mirrors `app/llm.py`'s `OpenAI` monkeypatch pattern) — no real
    SigNoz MCP server needed to test the wrapper contract.
  - `query_signoz(tool_name, arguments)` — the one public call site (MCP-02). Stamps
    `AGENTK_MCP_TOOL_NAME`/`AGENTK_MCP_QUERY_HASH` on the `signoz_mcp.query` span before the
    call (present regardless of outcome); marks the span `ERROR` on a transport exception
    (re-raised, never swallowed) or a tool-reported `isError=True` result (returned, not
    raised — caller decides); logs only tool name + hash, never the raw evidence payload
    (content-safety, mirrors `app/observability.py`'s discipline).
- `app/observability.py`: added `AGENTK_MCP_TOOL_NAME`, `AGENTK_MCP_QUERY_HASH` (D-06).
- `requirements.txt`: added `mcp==1.28.1`. `.env.example`: added `SIGNOZ_MCP_COMMAND`,
  `SIGNOZ_URL`, `SIGNOZ_API_KEY` (and, catching up a Phase-3 gap, `ADMIN_TOKEN`).
- `scripts/probe_signoz_mcp.py`: throwaway CLI script (mirrors `probe_ask_spans.py`'s
  style) — `python scripts/probe_signoz_mcp.py <tool_name> [<json_args>]` prints the query
  hash and the retrieved evidence content. Requires a **real** SigNoz MCP server binary +
  live SigNoz stack; not runnable in this sandboxed environment.
- `tests/test_signoz_mcp.py`: 7 tests — hash determinism (key-order-independent) and
  differentiation by tool/arguments; exactly one span + correct attributes on success;
  arguments passed through unchanged; span `ERROR` on tool-reported error (result still
  returned, not raised); span `ERROR` + exception re-raised on transport failure.

## Verification

- `pytest tests/test_signoz_mcp.py -q` — 7 passed.
- Full offline suite: 58 passed, 1 skipped (integration), no regressions.
- Grep: exactly one `.call_tool(` call site in the entire codebase (inside
  `_call_tool_via_mcp`, itself only called from `query_signoz`).

## What's not done — human verification (MCP-01, "not mocked" half)

Success Criterion 1 requires "a throwaway script retrieves a real trace, log, or metric
query result end-to-end (not mocked)". This environment has neither a SigNoz MCP server
binary nor a live SigNoz stack (same HV-2 gate carried from Phases 2/3), so that proof is
deferred to a human running `scripts/probe_signoz_mcp.py` against a real server once
available. The wrapper's span/hash contract (Success Criterion 2) is fully proven offline.
