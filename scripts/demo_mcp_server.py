#!/usr/bin/env python
"""DEMO FIXTURE — a stand-in SigNoz MCP server, for offline demos only.

**This is not SigNoz.** It is a real MCP stdio server that answers Agent K's
three evidence tools with hand-authored payloads shaped like SigNoz's, so the
whole pipeline — Law 1 evidence, Law 2's gate, Law 3's self-telemetry, the
rollback, the report — can be exercised on a laptop with no observability
backend running. Point `SIGNOZ_MCP_COMMAND`/`SIGNOZ_MCP_ARGS` at the real
`signoz-mcp-server` binary instead and nothing in `app/` changes.

Why a fixture exists at all: a live demo that depends on a freshly-ingested
backend fails in the ways demos fail — data not landed yet, a wrong ingestion
key, no network. This makes the *agent's* behaviour reproducible so what is
being shown is the agent, not the backend's mood.

**What it does NOT prove.** The evidence links it returns do not resolve, since
there is no SigNoz behind them. Law 1's "every link resolves" claim can only be
demonstrated against a real instance with `scripts/check_evidence_links.py`. Say
so when demoing; do not present fixture output as live telemetry.

Honest by construction in one important way: it reads the *live* flag state from
the running app's `/admin/flags`, so evidence follows whatever scenario is
actually switched on. Toggling a flag genuinely changes what Agent K sees, which
genuinely changes its diagnosis and the gate's verdict. Nothing is keyed off a
hardcoded answer, and there is no path by which the fixture can be told what to
conclude.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Mirrors app/investigation.py's tool names and app/observability.py's
# DEPLOYMENT_MARKER_SCENARIO. Duplicated as literals rather than imported so this
# script stays runnable as a bare subprocess with no package context.
TRACES_TOOL = "signoz_search_traces"
LOGS_TOOL = "signoz_search_logs"
AGGREGATE_TOOL = "signoz_aggregate_traces"
DEPLOYMENT_SCENARIO_FIELD = "deployment.scenario"

FLAG_NAMES = ("prompt_regression", "retry_storm", "retrieval_latency", "db_pool_exhaustion")
DEPLOYMENT_CLASS_FLAGS = {"prompt_regression", "retry_storm"}

# Baseline p95 per span, in nanoseconds — a healthy service.
HEALTHY_LATENCY = {
    "POST /ask": 780_000_000,
    "rag.retrieval": 120_000_000,
    "rag.prompt_construction": 3_000_000,
    "chat": 640_000_000,
    "SELECT agentk": 18_000_000,
}

# How each scenario distorts that baseline. These are the symptom fingerprints
# the model is expected to tell apart, so they are deliberately distinct:
# retrieval_latency is slow in `rag.retrieval` alone, retry_storm is slow in
# `chat` alone, db_pool_exhaustion is slow in the DB span and errors out.
SCENARIO_LATENCY = {
    "retrieval_latency": {"rag.retrieval": 2_600_000_000, "POST /ask": 3_300_000_000},
    "retry_storm": {"chat": 7_400_000_000, "POST /ask": 8_100_000_000},
    "db_pool_exhaustion": {"SELECT agentk": 4_900_000_000, "POST /ask": 5_400_000_000},
    "prompt_regression": {},  # not a latency fault at all — grounding degrades
}

SCENARIO_LOGS = {
    "prompt_regression": [
        "prompt template rendered with 0 retrieved documents in context block",
        "answer generated without grounding context; sources list empty",
        "prompt_construction: context_block_chars=0 expected>0",
    ],
    "retry_storm": [
        "llm call timed out after 2.0s; retrying (attempt 2/5)",
        "llm call timed out after 2.0s; retrying (attempt 3/5)",
        "llm call timed out after 2.0s; retrying (attempt 4/5)",
        "retry budget exhausted for chat completion",
    ],
    "retrieval_latency": [
        "pgvector similarity search took 2570ms (threshold 250ms)",
        "rag.retrieval slow: top_k=4 doc_count=4 elapsed_ms=2584",
    ],
    "db_pool_exhaustion": [
        "QueuePool limit of size 1 overflow 0 reached, connection timed out",
        "asyncpg: connection pool exhausted; waited 5.0s",
        "500 Internal Server Error on POST /ask",
    ],
}

HEALTHY_LOGS = [
    "POST /ask 200 in 812ms",
    "rag.retrieval returned 4 documents",
    "chat completion ok: 318 prompt tokens, 141 completion tokens",
]


async def active_scenarios() -> list[str]:
    """Read live flag state from the app under demo.

    On any failure the answer is "nothing is switched on" — a fixture that
    guessed a scenario here would be inventing an incident, which is exactly the
    thing this project exists to argue against.
    """
    base = os.environ.get("DEMO_RAG_URL") or "http://localhost:8000"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base.rstrip('/')}/admin/flags")
            response.raise_for_status()
            flags = response.json().get("flags", {})
    except Exception as exc:  # noqa: BLE001 - any failure means "no signal"
        print(f"[fixture] could not read flags from {base}: {exc}", file=sys.stderr)
        return []
    return [name for name in FLAG_NAMES if flags.get(name)]


def latency_rows(active: list[str]) -> list[list]:
    latency = dict(HEALTHY_LATENCY)
    for scenario in active:
        latency.update(SCENARIO_LATENCY.get(scenario, {}))
    return [[name, value] for name, value in latency.items()]


def deployment_rows(active: list[str]) -> list[list]:
    """Marker counts grouped by scenario.

    Returns rows only for deployment-class scenarios, mirroring FLAG-06: the two
    runtime faults emit no marker. The empty list is the load-bearing case — it
    is the positive evidence that a fault was *not* deployment-caused, which is
    what Law 2's deployment_related check turns on.
    """
    return [[s, 3] for s in active if s in DEPLOYMENT_CLASS_FLAGS]


def error_count_rows(active: list[str]) -> list[list]:
    if "db_pool_exhaustion" in active:
        return [["true", 47], ["false", 12]]
    if "retry_storm" in active:
        return [["true", 6], ["false", 88]]
    return [["false", 214]]


def error_span_rows(active: list[str]) -> list[dict]:
    if "db_pool_exhaustion" in active:
        return [
            {
                "traceId": f"db00{i:028x}",
                "name": "POST /ask",
                "durationNano": 5_400_000_000,
                "statusCode": 500,
                "statusMessage": "QueuePool limit of size 1 overflow 0 reached",
            }
            for i in range(3)
        ]
    if "retry_storm" in active:
        return [
            {
                "traceId": f"rs00{i:028x}",
                "name": "chat",
                "durationNano": 7_400_000_000,
                "statusCode": 504,
                "statusMessage": "llm call timed out; retry budget exhausted",
            }
            for i in range(2)
        ]
    # Silent for the latency scenarios by design - they degrade latency without
    # raising the error rate, which is why the query plan does not rely on this.
    return []


def log_rows(active: list[str]) -> list[dict]:
    bodies: list[str] = []
    for scenario in active:
        bodies.extend(SCENARIO_LOGS.get(scenario, []))
    if not bodies:
        bodies = list(HEALTHY_LOGS)
    return [
        {"timestamp": f"2026-07-25T12:{i:02d}:00Z", "severity": "ERROR" if active else "INFO", "body": body}
        for i, body in enumerate(bodies)
    ]


def classify_aggregate(arguments: dict) -> str:
    """Which of the three aggregate queries this is.

    signoz_aggregate_traces is used three ways by EVIDENCE_QUERY_PLAN, so the
    dispatch has to read the arguments, not just the tool name.
    """
    if arguments.get("operation") == "deployment.marker":
        return "deployment"
    group_by = arguments.get("groupBy")
    if group_by == "has_error":
        return "error_counts"
    if group_by == DEPLOYMENT_SCENARIO_FIELD:
        return "deployment"
    return "latency"


server = Server("agent-k-demo-fixture")


@server.list_tools()
async def list_tools() -> list[Tool]:
    schema = {"type": "object", "additionalProperties": True}
    return [
        Tool(name=TRACES_TOOL, description="DEMO FIXTURE: error spans", inputSchema=schema),
        Tool(name=LOGS_TOOL, description="DEMO FIXTURE: log records", inputSchema=schema),
        Tool(name=AGGREGATE_TOOL, description="DEMO FIXTURE: span aggregates", inputSchema=schema),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    active = await active_scenarios()

    if name == AGGREGATE_TOOL:
        kind = classify_aggregate(arguments)
        if kind == "deployment":
            payload = {
                "groupBy": DEPLOYMENT_SCENARIO_FIELD,
                "operation": "deployment.marker",
                "rows": deployment_rows(active),
            }
        elif kind == "error_counts":
            payload = {"groupBy": "has_error", "aggregation": "count", "rows": error_count_rows(active)}
        else:
            payload = {
                "groupBy": "name",
                "aggregation": "p95",
                "aggregateOn": "duration_nano",
                "unit": "nanoseconds",
                "rows": latency_rows(active),
            }
    elif name == TRACES_TOOL:
        payload = {"spans": error_span_rows(active)}
    elif name == LOGS_TOOL:
        payload = {"logs": log_rows(active)}
    else:
        raise ValueError(f"fixture does not implement tool {name!r}")

    # Marked in-band so a fixture payload is never mistaken for live telemetry,
    # including by anyone reading a captured investigation later.
    payload["_source"] = "agent-k demo fixture (NOT live SigNoz)"
    payload["_active_scenarios"] = active
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def main() -> None:
    print("[fixture] agent-k demo MCP fixture ready (NOT live SigNoz)", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
