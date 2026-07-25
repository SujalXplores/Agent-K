"""Agent K's investigation state machine (INV-01/02/03) with Law 1 evidence
linking (LAW1-04) and Law 3 self-telemetry, loop breaker, cost watchdog
(LAW3-01..06) instrumented inline.

run_investigation(alert) is a plain Python async function driving an explicit
RECEIVED -> INVESTIGATING -> {REPORTED | ESCALATED} loop (no agent framework, per
the locked scope decision) - each iteration issues evidence-gathering MCP queries
through app.signoz_mcp.query_signoz (the single call site from Phase 4) and forms
one hypothesis via app.llm.generate (the single LLM client from Phase 2), then
either stops (confident enough / evidence exhausted) or continues. Every MCP query
is hashed (signoz_mcp.compute_query_hash) and counted per investigation; if the
identical query repeats past loop_breaker_threshold(), the loop breaker stops
the investigation, records the event, and escalates with whatever partial evidence
was collected (LAW3-04). Evidence-gathering queries deliberately differ across
iterations (EVIDENCE_QUERY_PLAN) under normal operation, so the loop breaker only
fires on a genuine repeat (a bug or adversarial input forcing the same query),
never as a side effect of legitimate multi-iteration investigation.

Cost watchdog note (LAW3-05): app/observability.py's AGENTK_LLM_ESTIMATED_COST_USD
is deliberately pinned to $0 for the locked free-tier providers (Groq/Cerebras/
Gemini Flash have no real per-token cost during the hackathon) - a USD-denominated
budget could therefore never fire. The cost watchdog here budgets on TOKEN COUNT
instead (the practical, always-nonzero proxy the requirement's "token/cost usage"
wording explicitly allows), while still recording the real (zero) USD estimate via
the existing shared attribute for schema completeness.

start_investigation(alert) is the fire-and-forget entrypoint app/alerts_webhook.py
calls per received alert (INV-01) - it schedules run_investigation as a background
asyncio task so the webhook's HTTP response is never blocked on a multi-second
investigation.

Live-verification gaps (same HV pattern as Phases 2-4): the exact SigNoz MCP tool
names in EVIDENCE_QUERY_PLAN, and _extract_incident_span_context's trace_id/span_id
label convention for LAW1-04's span link, are both reasonable designs built without
a live SigNoz MCP server or a real alert payload to confirm against - see this
phase's SUMMARY for what needs confirming once a live stack exists.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.trace import Link, SpanContext, TraceFlags

from app import llm as llm_module
from app import policy as policy_module
from app import rollback as rollback_module
from app import signoz_mcp
from app.claims import (
    Claim,
    Evidence,
    build_evidence_link,
    recalibrate_confidence,
    strip_unevidenced_claims,
)
from app.flags import FLAG_NAMES
from app.observability import (
    AGENTK_HYPOTHESIS_CONFIDENCE,
    AGENTK_HYPOTHESIS_LLM_CONFIDENCE,
    AGENTK_INVESTIGATION_DURATION_S,
    AGENTK_INVESTIGATION_HYPOTHESIS_COUNT,
    AGENTK_INVESTIGATION_ID,
    AGENTK_INVESTIGATION_INCOMPLETE,
    AGENTK_INVESTIGATION_MCP_QUERY_COUNT,
    AGENTK_INVESTIGATION_MCP_QUERY_FAILURES,
    AGENTK_INVESTIGATION_REPEATED_QUERY_COUNT,
    AGENTK_INVESTIGATION_STATE,
    AGENTK_INVESTIGATION_TOTAL_TOKENS,
    AGENTK_WATCHDOG_BUDGET,
    AGENTK_WATCHDOG_KIND,
    AGENTK_WATCHDOG_QUERY_HASH,
    AGENTK_WATCHDOG_REPEAT_COUNT,
    AGENTK_WATCHDOG_TOTAL_TOKENS,
    DEPLOYMENT_MARKER_SCENARIO,
)

if TYPE_CHECKING:
    import asyncio

    from app.alerts_webhook import AlertItem

logger = logging.getLogger(__name__)

# --- Tunables ---
# Tool names verified against signoz-mcp-server v0.9.0's advertised tool list on
# 2026-07-25. They were previously guessed as query_traces/query_logs/query_metrics,
# which do not exist - every evidence query would have failed, stripping every claim
# and escalating every investigation.
SIGNOZ_TRACES_TOOL = "signoz_search_traces"
SIGNOZ_LOGS_TOOL = "signoz_search_logs"
SIGNOZ_TRACE_STATS_TOOL = "signoz_aggregate_traces"

# Sized against Groq's free tier, which is the binding constraint: 6000 tokens per
# minute, and one investigation makes up to MAX_ITERATIONS LLM calls inside a few
# seconds. A 20-row trace search alone measured 8424 tokens on 2026-07-25 and was
# rejected with HTTP 413 before any hypothesis could be formed.
# The span attribute FLAG-06's marker carries the scenario name in. Imported from
# app/observability.py rather than written inline (D-06), so the query Agent K
# groups by can never drift from the attribute the emitter actually sets.
DEPLOYMENT_SCENARIO_FIELD = DEPLOYMENT_MARKER_SCENARIO

EVIDENCE_ROW_LIMIT = 5
MAX_EVIDENCE_CHARS = 4000  # per iteration, after null-stripping
DEFAULT_TIME_RANGE = "1h"  # relative fallback when the alert carries no usable window


# Keys carrying SigNoz's own query-engine statistics and result-set plumbing, not
# telemetry about the incident. They are stripped because a live eval run caught the
# model diagnosing FROM them - it claimed "db_pool_exhaustion is likely due to an
# extremely high number of rows scanned (1018) and bytes scanned (10434)", which are
# the query planner's stats for Agent K's own query. Evidence must describe the
# incident, never the act of looking at it.
_ENGINE_NOISE_KEYS = frozenset({
    "meta", "rowsScanned", "bytesScanned", "durationMs", "stepIntervals",
    "nextCursor", "queryName", "columnType", "aggregationIndex", "signal",
    "fieldContext", "fieldDataType", "id", "warnings",
})


def _strip_nulls(node):
    """Drop null-valued keys from a decoded MCP payload.

    SigNoz returns every possible span attribute per row, and for this app the vast
    majority are null (k8s.*, cloud.*, db.*, http.* on non-HTTP spans). They are
    pure token cost with zero diagnostic signal, so removing them shrinks the
    prompt by roughly an order of magnitude WITHOUT discarding anything the model
    could have reasoned from - which blind truncation cannot promise.
    """
    if isinstance(node, dict):
        return {
            k: _strip_nulls(v)
            for k, v in node.items()
            if v is not None and k not in _ENGINE_NOISE_KEYS
        }
    if isinstance(node, list):
        return [_strip_nulls(item) for item in node]
    return node


def compact_evidence(text: str) -> str:
    """Shrink one tool result to something that fits in a free-tier prompt.

    Null-strips when the payload is JSON, then hard-caps the length. The cap is a
    visible marker, never a silent cut: a truncated payload the model reasons over
    must be identifiable as truncated when auditing why a claim was made.

    Only the LLM PROMPT is affected. Law 1 publishes the query and the evidence
    link, never this raw content, so compaction cannot weaken an evidence trail -
    the link still resolves to the complete data in SigNoz.
    """
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        compacted = json.dumps(_strip_nulls(json.loads(text[start:end])), separators=(",", ":"))
    except (ValueError, json.JSONDecodeError):
        compacted = text

    if len(compacted) <= MAX_EVIDENCE_CHARS:
        return compacted
    dropped = len(compacted) - MAX_EVIDENCE_CHARS
    return f"{compacted[:MAX_EVIDENCE_CHARS]}\n...[truncated {dropped} chars of evidence]"


def _latency_by_operation_args(service: str, time_args: dict) -> dict:
    """p95 latency per operation - the symptom, for EVERY scenario.

    Replaces an error-spans-only query that could not see half the incidents:
    retrieval_latency and db_pool_exhaustion degrade LATENCY without necessarily
    raising the error rate, so an `error=true` filter returned nothing for them and
    the model was left diagnosing from an empty result set. Grouping p95 by span
    name localises the fault instead - a slow `rag.retrieval` and a slow `chat` are
    different incidents, and that distinction is the whole diagnosis.
    """
    return {
        "aggregation": "p95",
        "aggregateOn": "duration_nano",
        "groupBy": "name",
        "service": service,
        **time_args,
    }


def _error_spans_args(service: str, time_args: dict) -> dict:
    """Error spans, when there are any. Silent for the latency scenarios by design."""
    return {"service": service, "error": "true", "limit": EVIDENCE_ROW_LIMIT, **time_args}


def _deployment_marker_args(service: str, time_args: dict) -> dict:
    """deployment.marker spans grouped BY SCENARIO - the CAUSE signal.

    Aggregated rather than searched, because signoz_search_traces returns only
    canonical span columns and drops custom attributes: a raw marker row shows
    `name: deployment.marker` but NOT which scenario it marks. The first live run
    proved the cost of that - the model could see markers existed, had no way to
    tell prompt_regression from retry_storm, and guessed wrong. Grouping by the
    attribute returns the scenario NAMES:

        [["retry_storm", 24], ["prompt_regression", 3]]

    Its ABSENCE is as informative as its presence: FLAG-06 emits a marker only for
    prompt_regression and retry_storm, so no marker in the incident window is
    positive evidence that the cause was NOT a deployment - exactly the distinction
    Law 2's deployment_related check turns on.
    """
    return {
        "aggregation": "count",
        "groupBy": DEPLOYMENT_SCENARIO_FIELD,
        "operation": "deployment.marker",
        "service": service,
        **time_args,
    }


def _log_search_args(service: str, time_args: dict) -> dict:
    return {"service": service, "limit": EVIDENCE_ROW_LIMIT, **time_args}


def _trace_stats_args(service: str, time_args: dict) -> dict:
    """Error/success span counts for the service.

    Deliberately NOT signoz_query_metrics: that tool requires a `metricName`, and
    this app emits no custom metrics - only auto-instrumented spans. Counting spans
    grouped by has_error derives the error-rate signal from telemetry we actually
    produce, instead of querying a metric that does not exist.
    """
    return {"aggregation": "count", "groupBy": "has_error", "service": service, **time_args}


# Each iteration issues the next entry - guarantees no repeated query under normal
# operation (see module docstring). MAX_ITERATIONS is pinned to this plan's length
# so the loop never has to clamp/reuse an earlier entry.
EVIDENCE_QUERY_PLAN: list[tuple[str, str, Callable[[str, dict], dict]]] = [
    (SIGNOZ_TRACE_STATS_TOOL, "metric", _latency_by_operation_args),
    (SIGNOZ_TRACE_STATS_TOOL, "deployment", _deployment_marker_args),
    (SIGNOZ_TRACES_TOOL, "trace", _error_spans_args),
    (SIGNOZ_LOGS_TOOL, "log", _log_search_args),
    (SIGNOZ_TRACE_STATS_TOOL, "metric", _trace_stats_args),
]
MAX_ITERATIONS = len(EVIDENCE_QUERY_PLAN)


DEFAULT_LOOP_BREAKER_REPEAT_THRESHOLD = 3  # same query hash seen more than this many times -> stop
DEFAULT_TOKEN_BUDGET = 20_000  # total input+output tokens per investigation (see cost-watchdog note above)
CONFIDENCE_STOP_THRESHOLD = 0.75  # stop iterating once a hypothesis is this confident


def loop_breaker_threshold() -> int:
    """The loop-breaker repeat threshold, overridable via env (LAW3-04).

    Read at call time rather than captured at import so a demo can tighten the
    threshold and watch the guardrail genuinely fire, on this same code path,
    without a rebuild. The guardrail itself is unchanged - only the number it
    compares against moves. An unparseable value falls back to the default
    rather than raising: a malformed demo env var must not be able to disable a
    safety guardrail.
    """
    try:
        return int(os.environ["AGENT_K_LOOP_BREAKER_THRESHOLD"])
    except (KeyError, ValueError):
        return DEFAULT_LOOP_BREAKER_REPEAT_THRESHOLD


def token_budget() -> int:
    """The per-investigation token budget, overridable via env (LAW3-05).

    Same rationale as loop_breaker_threshold(): setting this low makes the cost
    watchdog fire for real instead of being asserted only in tests.
    """
    try:
        return int(os.environ["AGENT_K_TOKEN_BUDGET"])
    except (KeyError, ValueError):
        return DEFAULT_TOKEN_BUDGET

# The confidence stop cannot fire before this many evidence queries have run.
# Without it the first hypothesis almost always ends the investigation: the model
# readily returns 0.9+, which clears the stop threshold on iteration 1. The first
# live run did exactly that - one trace query, then done, having never looked at
# the deployment marker that decides the deployment_related policy check. A
# confident answer drawn from one query is not a completed investigation.
MIN_EVIDENCE_ITERATIONS = 2

# The deployment-marker query MUST run before the confidence stop is allowed to
# fire. The Law 2 gate now requires an observed marker to corroborate a
# deployment-class claim, so an investigation that stopped before this query could
# never approve anything - the marker evidence simply would not exist yet. Ordering
# is load-bearing, so it is asserted at import rather than left to a comment.
_DEPLOYMENT_QUERY_INDEX = next(
    i for i, (_, ev_type, _) in enumerate(EVIDENCE_QUERY_PLAN) if ev_type == "deployment"
)
assert _DEPLOYMENT_QUERY_INDEX < MIN_EVIDENCE_ITERATIONS, (
    "the deployment-marker query must fall within MIN_EVIDENCE_ITERATIONS, or the "
    "policy gate can never corroborate a deployment-class claim"
)

# Known incident vocabulary - matches app.flags.FLAG_NAMES exactly (Phase 3's four
# seeded scenarios), given to the LLM so it can name a scenario rather than
# inventing free-form root causes.
KNOWN_INCIDENT_TYPES = ("prompt_regression", "retry_storm", "retrieval_latency", "db_pool_exhaustion")

INVESTIGATION_SYSTEM_PROMPT = (
    "You are Agent K, an automated incident-response investigator. You are given "
    "SigNoz evidence (traces/logs/metrics) gathered for a firing alert.\n\n"
    "Identify the most likely root cause. It MUST be one of these known failure "
    f"scenarios: {', '.join(KNOWN_INCIDENT_TYPES)} - or 'unknown' if the evidence "
    "does not clearly match one.\n\n"
    "Your claim sentence MUST begin with the scenario name exactly as written above "
    "(or 'unknown'), then explain. A claim that does not start with one of those "
    "exact names cannot be acted on and will be discarded.\n\n"
    "A deployment.marker span in the evidence is strong support for a "
    "deployment-class cause (prompt_regression or retry_storm); its absence is "
    "evidence AGAINST one. Do not diagnose a scenario the evidence does not show, "
    "and prefer 'unknown' over a confident guess.\n\n"
    "Respond with ONLY a JSON object of the exact shape "
    '{"claim": "<scenario_name>: <one sentence explanation>", "confidence": <0.0-1.0>}.'
)


class InvestigationState(str, Enum):
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    REPORTED = "reported"
    ESCALATED = "escalated"


@dataclass
class Investigation:
    """One investigation's full record - the in-process store's value type.

    `last_evidence_text` is internal per-iteration working state (raw evidence
    content fed to the LLM prompt) - not part of the published Claim/Evidence
    schema (LAW1-01 only publishes query/time_range/link, never raw content).
    """

    id: str
    alert: AlertItem
    state: InvestigationState = InvestigationState.RECEIVED
    claims: list[Claim] = field(default_factory=list)
    started_at: float = field(default_factory=time.monotonic)
    mcp_query_count: int = 0
    mcp_query_failures: int = 0
    query_hash_counts: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    incomplete: bool = False
    loop_breaker_fired: bool = False
    cost_watchdog_fired: bool = False
    # Wall-duration of the investigation, stamped once it reaches a terminal state.
    # Stays None only if the process died mid-investigation. Kept on the record (not
    # just on the span) so Phase 7's report page can show the same Law 3 number a
    # human would otherwise have to open SigNoz to read.
    duration_s: float | None = None
    watchdog_events: list[dict] = field(default_factory=list)
    last_evidence_text: list[str] = field(default_factory=list)
    # Law 2 act-stage record (Phase 6). Both stay None for an incomplete
    # investigation, which never reaches the act stage - see _run_act_stage.
    policy_decision: policy_module.PolicyDecision | None = None
    action_outcome: rollback_module.ActionOutcome | None = None
    # SigNoz time-window arguments, frozen ONCE at construction (see __post_init__).
    time_args: dict = field(default_factory=dict)
    # Scenario names for which a real deployment.marker was OBSERVED in evidence.
    # The Law 2 gate requires this to corroborate a deployment-class claim, so it
    # must only ever be populated from a tool result - never from a claim.
    deployment_markers_seen: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Freeze the evidence time window for the whole investigation.

        This MUST NOT be recomputed per query. An open-ended alert's window ends at
        "now", so recomputing it per iteration puts a moving millisecond into the
        query arguments - which changes the query hash every time and makes the
        LAW3-04 loop breaker structurally unable to fire, since two identical
        queries would never hash alike. Freezing it here also means every piece of
        evidence in one investigation describes the same window, which is what
        makes the claims comparable to each other.
        """
        if not self.time_args:
            self.time_args = build_time_args(self.alert)


# In-process investigation store (mirrors app.alerts_webhook's `_alerts` list
# pattern) - sufficient for this phase; Phase 7's report page reads from this.
_investigations: dict[str, Investigation] = {}


def get_investigation(investigation_id: str) -> Investigation | None:
    return _investigations.get(investigation_id)


def list_investigations() -> list[Investigation]:
    return list(_investigations.values())


def clear_investigations() -> None:
    """Reset the in-process store (test-support / demo reset)."""
    _investigations.clear()


def _record_mcp_query_and_check_loop(inv: Investigation, tool_name: str, arguments: dict) -> str | None:
    """Increment the query-hash repeat counter (LAW3-02); return the hash if the
    loop-breaker threshold was just exceeded (caller must stop), else None."""
    query_hash = signoz_mcp.compute_query_hash(tool_name, arguments)
    inv.query_hash_counts[query_hash] = inv.query_hash_counts.get(query_hash, 0) + 1
    if inv.query_hash_counts[query_hash] > loop_breaker_threshold():
        return query_hash
    return None


def _fire_loop_breaker(inv: Investigation, query_hash: str) -> None:
    """Stop the investigation, record the loop event, escalate (LAW3-04/06)."""
    inv.state = InvestigationState.ESCALATED
    inv.incomplete = True
    inv.loop_breaker_fired = True
    repeat_count = inv.query_hash_counts[query_hash]
    inv.watchdog_events.append(
        {"kind": "loop_breaker", "query_hash": query_hash, "repeat_count": repeat_count}
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.watchdog.loop_breaker") as span:
        span.set_attribute(AGENTK_WATCHDOG_KIND, "loop_breaker")
        span.set_attribute(AGENTK_WATCHDOG_QUERY_HASH, query_hash)
        span.set_attribute(AGENTK_WATCHDOG_REPEAT_COUNT, repeat_count)
    logger.error("loop breaker fired: query_hash=%s repeat_count=%d", query_hash, repeat_count)


def _fire_cost_watchdog(inv: Investigation) -> None:
    """Stop the investigation, record the cost event, escalate (LAW3-05)."""
    inv.state = InvestigationState.ESCALATED
    inv.incomplete = True
    inv.cost_watchdog_fired = True
    budget = token_budget()
    inv.watchdog_events.append(
        {"kind": "cost_budget", "total_tokens": inv.total_tokens, "budget": budget}
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.watchdog.cost_budget") as span:
        span.set_attribute(AGENTK_WATCHDOG_KIND, "cost_budget")
        span.set_attribute(AGENTK_WATCHDOG_TOTAL_TOKENS, inv.total_tokens)
        span.set_attribute(AGENTK_WATCHDOG_BUDGET, budget)
    logger.error("cost watchdog fired: total_tokens=%d budget=%d", inv.total_tokens, budget)


def _parse_iso_to_ms(value: str | None) -> int | None:
    """ISO-8601 (with or without a trailing Z) -> unix milliseconds, or None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def build_time_args(alert: AlertItem) -> dict:
    """The time-window arguments every SigNoz MCP evidence tool accepts.

    The tools take EITHER `start`/`end` as unix milliseconds (which win when both
    are given) OR a relative `timeRange` like '1h'. The alert's own window is
    preferred so evidence is scoped to the incident rather than to "recently";
    anything unusable about that window falls back to the relative default rather
    than sending a nonsense range.
    """
    start_ms = _parse_iso_to_ms(alert.startsAt)
    if start_ms is None:
        return {"timeRange": DEFAULT_TIME_RANGE}

    end_ms = _parse_iso_to_ms(alert.endsAt) or int(time.time() * 1000)
    if end_ms <= start_ms:
        return {"timeRange": DEFAULT_TIME_RANGE}
    return {"start": start_ms, "end": end_ms}


_WEB_URL_PATTERN = re.compile(r'"webUrl"\s*:\s*"([^"]+)"')


def extract_web_url(text: str) -> str | None:
    """Pull SigNoz's own deep link out of a tool result, when it provides one.

    signoz-mcp-server returns a `webUrl` on its resource-read tools - an absolute,
    server-generated link to the exact resource. Preferring it over a hand-built
    URL is what makes LAW1-05's "100% resolve" achievable: SigNoz's own link cannot
    disagree with SigNoz's own routes, whereas app/claims.py's path shapes are an
    unverified guess.
    """
    match = _WEB_URL_PATTERN.search(text)
    return match.group(1) if match else None


async def _gather_evidence(inv: Investigation, alert: AlertItem, iteration: int) -> list[Evidence]:
    """Issue one iteration's evidence-gathering MCP query (LAW3-02).

    Every MCP call goes through signoz_mcp.query_signoz (MCP-02's single call
    site) - this function never calls the MCP SDK directly. `iteration` selects
    the query from EVIDENCE_QUERY_PLAN, so a normal multi-iteration investigation
    never repeats a query (see module docstring).
    """
    service = alert.labels.get("service", "unknown-service")
    time_range = f"{alert.startsAt}/{alert.endsAt or 'now'}"
    tool_name, ev_type, build_args = EVIDENCE_QUERY_PLAN[iteration]
    arguments = build_args(service, inv.time_args)

    triggered_hash = _record_mcp_query_and_check_loop(inv, tool_name, arguments)
    if triggered_hash is not None:
        _fire_loop_breaker(inv, triggered_hash)
        return []

    inv.mcp_query_count += 1
    try:
        result = await signoz_mcp.query_signoz(tool_name, arguments)
    except Exception:
        inv.mcp_query_failures += 1
        logger.warning("evidence-gathering query failed: tool=%s", tool_name)
        return []

    if result.isError:
        inv.mcp_query_failures += 1
        return []

    content_text = "\n".join(getattr(block, "text", "") for block in result.content)
    inv.last_evidence_text.append(compact_evidence(content_text))

    # Record which deployment markers genuinely exist, straight from the tool
    # result. This is what the policy gate corroborates a deployment-class claim
    # against, so it is deliberately read from EVIDENCE and never from claim text.
    if ev_type == "deployment":
        inv.deployment_markers_seen.update(
            name for name in FLAG_NAMES if f'"{name}"' in content_text
        )
    # Prefer SigNoz's own deep link over a hand-built one (see extract_web_url).
    link = extract_web_url(content_text) or build_evidence_link(ev_type, service, time_range)
    return [
        Evidence(
            type=ev_type,
            query=f"{tool_name}({arguments})",
            time_range=time_range,
            link=link,
        )
    ]


def _parse_hypothesis_response(answer: str) -> tuple[float, str]:
    """Parse the LLM's requested JSON hypothesis; fall back to a low-confidence,
    unparsed-response claim if the model didn't follow the requested format
    (LLM output format compliance is never guaranteed)."""
    try:
        data = json.loads(answer)
        claim_text = str(data["claim"])
        llm_confidence = max(0.0, min(1.0, float(data["confidence"])))
        return llm_confidence, claim_text
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.warning("could not parse hypothesis response as structured JSON")
        return 0.1, f"unparsed model response: {answer[:200]}"


async def _form_hypothesis(inv: Investigation, alert: AlertItem, evidence: list[Evidence]) -> Claim | None:
    """Form one root-cause hypothesis from evidence gathered so far (LAW1-03).

    Returns None when no evidence was gathered this iteration (loop-breaker or
    query-failure case) - nothing to hypothesize about yet.
    """
    if not evidence:
        return None

    evidence_text = "\n".join(inv.last_evidence_text)
    alertname = alert.labels.get("alertname", "unknown")
    prompt = (
        f"Alert: {alertname}\nEvidence gathered so far:\n{evidence_text}\n\n"
        "What is the most likely root cause?"
    )

    result = llm_module.generate(prompt, system=INVESTIGATION_SYSTEM_PROMPT)
    inv.total_tokens += (result.input_tokens or 0) + (result.output_tokens or 0)

    llm_confidence, claim_text = _parse_hypothesis_response(result.answer)
    deployment_marker_present = any("deployment" in text.lower() for text in inv.last_evidence_text)
    confidence = recalibrate_confidence(
        llm_confidence, evidence, deployment_marker_present=deployment_marker_present
    )
    claim = Claim(claim=claim_text, confidence=confidence, evidence=evidence)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.hypothesis") as span:
        span.set_attribute(AGENTK_HYPOTHESIS_CONFIDENCE, confidence)
        span.set_attribute(AGENTK_HYPOTHESIS_LLM_CONFIDENCE, llm_confidence)

    if inv.total_tokens > token_budget():
        _fire_cost_watchdog(inv)

    return claim


def _extract_incident_span_context(alert: AlertItem) -> SpanContext | None:
    """Best-effort extraction of the original incident's trace/span IDs for
    LAW1-04's span link.

    CONVENTION (not yet live-confirmed): looks for `trace_id`/`span_id` hex
    strings in the alert's labels or annotations. SigNoz's real alert payload's
    actual field names for this must be confirmed once a live alert is observed
    (paired with LAW1-05's live link-check gap) - this is a documented
    live-verification item, not an assumption this code silently relies on.
    """
    source = {**alert.labels, **alert.annotations}
    trace_id_hex = source.get("trace_id")
    span_id_hex = source.get("span_id")
    if not trace_id_hex or not span_id_hex:
        return None
    try:
        trace_id = int(trace_id_hex, 16)
        span_id = int(span_id_hex, 16)
    except ValueError:
        return None
    if trace_id == 0 or span_id == 0:
        return None
    return SpanContext(
        trace_id=trace_id, span_id=span_id, is_remote=True, trace_flags=TraceFlags(TraceFlags.SAMPLED)
    )


def _build_incident_links(alert: AlertItem) -> list[Link]:
    span_context = _extract_incident_span_context(alert)
    if span_context is None:
        return []
    return [Link(span_context)]


async def _run_act_stage(inv: Investigation, alert: AlertItem) -> None:
    """Propose an action, run it past the Law 2 policy gate, and act only if allowed.

    Deliberately skipped for an INCOMPLETE investigation (loop breaker or cost
    watchdog fired, or an unexpected exception escalated it): an investigation
    that stopped early by definition did not finish gathering evidence, and
    acting on a half-formed picture is precisely the failure mode Law 3's
    watchdogs exist to prevent. Such an investigation escalates to a human
    instead (REPT-03 renders it as needs-human), with no policy decision recorded
    - honest silence rather than a verdict on evidence Agent K never collected.

    Every action Agent K could take passes through evaluate_policy() here, and
    app/rollback.py independently re-checks `decision.approved` before executing,
    so the gate cannot be bypassed by a caller that forgets to check.
    """
    if inv.incomplete or not inv.claims:
        return

    decision = policy_module.evaluate_policy(
        action=policy_module.ROLLBACK_ACTION,
        incident_id=inv.id,
        alert=alert,
        claims=inv.claims,
        deployment_markers=inv.deployment_markers_seen,
    )
    inv.policy_decision = decision

    if not decision.approved:
        # LAW2-05: no action; the decision already carries the evidence-linked
        # recommendation for a human.
        return

    time_range = f"{alert.startsAt}/{alert.endsAt or 'now'}"
    inv.action_outcome = await rollback_module.execute_rollback(
        decision=decision, time_range=time_range
    )


async def run_investigation(alert: AlertItem) -> Investigation:
    """Drive one investigation from RECEIVED to a terminal REPORTED/ESCALATED
    state (INV-02), producing at least one evidence-backed hypothesis when
    possible (INV-03), with Law 3 self-telemetry stamped on the parent span.

    Always reaches a terminal state and is recorded in the in-process store -
    an unexpected exception inside the loop is caught and converted into an
    incomplete ESCALATED investigation rather than propagating, so a single bad
    iteration can never leave an investigation with no record at all.
    """
    inv = Investigation(id=str(uuid.uuid4()), alert=alert)
    inv.state = InvestigationState.INVESTIGATING

    tracer = trace.get_tracer(__name__)
    links = _build_incident_links(alert)
    with tracer.start_as_current_span("agentk.investigation", links=links) as span:
        try:
            for iteration in range(MAX_ITERATIONS):
                inv.last_evidence_text = []
                evidence = await _gather_evidence(inv, alert, iteration)
                if inv.loop_breaker_fired:
                    break

                hypothesis = await _form_hypothesis(inv, alert, evidence)
                if hypothesis is not None:
                    inv.claims.append(hypothesis)
                if inv.cost_watchdog_fired:
                    break
                if (
                    hypothesis is not None
                    and iteration + 1 >= MIN_EVIDENCE_ITERATIONS
                    and hypothesis.confidence >= CONFIDENCE_STOP_THRESHOLD
                ):
                    break
        except Exception:
            logger.exception("investigation failed unexpectedly")
            inv.incomplete = True
            inv.state = InvestigationState.ESCALATED

        inv.claims = strip_unevidenced_claims(inv.claims)  # LAW1-02

        if not inv.loop_breaker_fired and not inv.cost_watchdog_fired and inv.state != InvestigationState.ESCALATED:
            if inv.claims:
                inv.state = InvestigationState.REPORTED
            else:
                inv.state = InvestigationState.ESCALATED
                inv.incomplete = True

        # Law 2 act stage (Phase 6). Runs inside the investigation span so the
        # policy-decision and action spans are its children - a human opening
        # agentk.investigation sees the reasoning AND the resulting verdict/action
        # in one trace. Guarded: a failure in the act stage must never destroy the
        # investigation record that Law 1/3 telemetry depends on.
        try:
            await _run_act_stage(inv, alert)
        except Exception:
            logger.exception("act stage failed unexpectedly")

        duration_s = time.monotonic() - inv.started_at
        inv.duration_s = duration_s
        span.set_attribute(AGENTK_INVESTIGATION_ID, inv.id)
        span.set_attribute(AGENTK_INVESTIGATION_STATE, inv.state.value)
        span.set_attribute(AGENTK_INVESTIGATION_INCOMPLETE, inv.incomplete)
        span.set_attribute(AGENTK_INVESTIGATION_DURATION_S, duration_s)
        span.set_attribute(AGENTK_INVESTIGATION_MCP_QUERY_COUNT, inv.mcp_query_count)
        span.set_attribute(AGENTK_INVESTIGATION_MCP_QUERY_FAILURES, inv.mcp_query_failures)
        span.set_attribute(
            AGENTK_INVESTIGATION_REPEATED_QUERY_COUNT,
            sum(1 for count in inv.query_hash_counts.values() if count > 1),
        )
        span.set_attribute(AGENTK_INVESTIGATION_HYPOTHESIS_COUNT, len(inv.claims))
        span.set_attribute(AGENTK_INVESTIGATION_TOTAL_TOKENS, inv.total_tokens)

    _investigations[inv.id] = inv
    return inv


def start_investigation(alert: AlertItem) -> asyncio.Task:
    """Schedule a background investigation for one alert (INV-01).

    Fire-and-forget: the webhook handler calling this must never block the HTTP
    response on a multi-second investigation. run_investigation already converts
    ordinary evidence/hypothesis failures into a terminal ESCALATED state; this
    wrapper is a last-resort guard so a truly unexpected exception is at least
    logged rather than surfacing only as an unawaited-task warning.
    """
    import asyncio as _asyncio

    async def _run_and_guard() -> Investigation:
        try:
            return await run_investigation(alert)
        except Exception:
            logger.exception("investigation task crashed outside run_investigation's own guard")
            raise

    return _asyncio.create_task(_run_and_guard())
