"""Throwaway end-to-end probe: retrieve real SigNoz evidence via app.signoz_mcp (MCP-01).

Unlike scripts/probe_ask_spans.py, this script requires a REAL SigNoz MCP server
binary and a live SigNoz stack - it is not exercisable in an offline/sandboxed
environment and is a human-verification step (mirrors Phase 2/3's HV-1/HV-2 pattern).

Prereqs (set in .env or the shell environment):
  SIGNOZ_MCP_COMMAND - path to the signoz-mcp-server executable (default ./signoz-mcp-server)
  SIGNOZ_URL         - the running SigNoz instance's base URL
  SIGNOZ_API_KEY     - a valid SigNoz API key

Usage:
  python scripts/probe_signoz_mcp.py <tool_name> [<json_arguments>]

Example (exact tool name/arguments depend on the SigNoz MCP server's actual tool
list - run `session.list_tools()` first if unsure, or check the server's docs):
  python scripts/probe_signoz_mcp.py list_traces '{"limit": 1}'

Prints the query hash (proves MCP-02's wrapper ran) and the retrieved evidence
content, so the operator can eyeball that a real (not mocked) trace/log/metric
came back.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Running this file directly puts the script's own directory on sys.path, not the
# repo root, so `import app.*` would fail. Add the repo root explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main(tool_name: str, arguments: dict) -> None:
    from app.signoz_mcp import compute_query_hash, query_signoz

    print(f"query hash: {compute_query_hash(tool_name, arguments)}")
    result = await query_signoz(tool_name, arguments)
    print(f"isError: {result.isError}")
    print("content:")
    for block in result.content:
        print(block)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(
            "usage: python scripts/probe_signoz_mcp.py <tool_name> [<json_arguments>]",
            file=sys.stderr,
        )
        sys.exit(1)
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) == 3 else {}
    asyncio.run(main(tool, args))
