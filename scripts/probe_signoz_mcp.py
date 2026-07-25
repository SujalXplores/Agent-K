"""Throwaway end-to-end probe: retrieve real SigNoz evidence via app.signoz_mcp (MCP-01).

Unlike scripts/probe_ask_spans.py, this script requires a REAL SigNoz MCP server
binary and a live SigNoz stack - it is not exercisable in an offline/sandboxed
environment and is a human-verification step (mirrors Phase 2/3's HV-1/HV-2 pattern).

Prereqs (set in .env or the shell environment):
  SIGNOZ_MCP_COMMAND - path to the signoz-mcp-server executable (default ./signoz-mcp-server)
  SIGNOZ_URL         - the running SigNoz instance's base URL
  SIGNOZ_API_KEY     - a valid SigNoz API key

Usage:
  python scripts/probe_signoz_mcp.py --list-tools
  python scripts/probe_signoz_mcp.py <tool_name> [<json_arguments>]

ALWAYS RUN --list-tools FIRST against a new server. Agent K originally shipped with
guessed tool names (query_traces/query_logs/query_metrics) that do not exist in
signoz-mcp-server; nothing surfaced that until the real list was printed, because a
bad tool name just returns an error result and looks like "no evidence found".

Example:
  python scripts/probe_signoz_mcp.py signoz_search_traces '{"service": "agent-k-rag-service", "limit": 1}'

Prints the query hash (proves MCP-02's wrapper ran) and the retrieved evidence
content, so the operator can eyeball that a real (not mocked) trace/log/metric
came back.
"""

from __future__ import annotations

import asyncio
import json
import sys


async def list_tools() -> None:
    """Print the server's real tool inventory, with each tool's input schema.

    Goes through the MCP SDK directly rather than app.signoz_mcp, because that
    module's single-call-site rule (MCP-02) is deliberately about call_tool - it
    exposes no list_tools path, and adding one would widen a surface that exists
    to stay narrow.
    """
    import os

    from dotenv import load_dotenv
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    load_dotenv()
    command = os.getenv("SIGNOZ_MCP_COMMAND", "./signoz-mcp-server")
    params = StdioServerParameters(
        command=command,
        env={
            "SIGNOZ_URL": os.getenv("SIGNOZ_URL", ""),
            "SIGNOZ_API_KEY": os.getenv("SIGNOZ_API_KEY", ""),
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            print(f"{len(result.tools)} tools advertised:\n")
            for tool in result.tools:
                print(f"  {tool.name}")
                props = (tool.inputSchema or {}).get("properties", {})
                required = set((tool.inputSchema or {}).get("required", []))
                for key in sorted(props):
                    mark = "*" if key in required else " "
                    print(f"      {mark} {key}")


async def main(tool_name: str, arguments: dict) -> None:
    from app.signoz_mcp import compute_query_hash, query_signoz

    print(f"query hash: {compute_query_hash(tool_name, arguments)}")
    result = await query_signoz(tool_name, arguments)
    print(f"isError: {result.isError}")
    print("content:")
    for block in result.content:
        print(block)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("--list-tools", "-l"):
        asyncio.run(list_tools())
        sys.exit(0)
    if len(sys.argv) not in (2, 3):
        print(
            "usage: python scripts/probe_signoz_mcp.py --list-tools\n"
            "       python scripts/probe_signoz_mcp.py <tool_name> [<json_arguments>]",
            file=sys.stderr,
        )
        sys.exit(1)
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) == 3 else {}
    asyncio.run(main(tool, args))
