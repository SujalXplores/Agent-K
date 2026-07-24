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
identical query repeats past LOOP_BREAKER_REPEAT_THRESHOLD, the loop breaker stops
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
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.trace import Link, SpanContext, TraceFlags

from app import llm as llm_module
from app import policy as policy_module
from app import rollback as rollback_module
from app import signoz_mcp
from app.claims import Claim, Evidence, build_evidence_link, recalibrate_confidence, strip_unevidenced_claims
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
)

if TYPE_CHECKING:
    import asyncio

    from app.alerts_webhook import AlertItem

logger = logging.getLogger(__name__)

# --- Tunables ---
SIGNOZ_TRACES_TOOL = "query_traces"
SIGNOZ_LOGS_TOOL = "query_logs"
SIGNOZ_METRICS_TOOL = "query_metrics"

# Each iteration issues the next entry - guarantees no repeated query under normal
# operation (see module docstring). MAX_ITERATIONS is pinned to this plan's length
# so the loop never has to clamp/reuse an earlier entry.
EVIDENCE_QUERY_PLAN: list[tuple[str, str]] = [
    (SIGNOZ_TRACES_TOOL, "trace"),
    (SIGNOZ_LOGS_TOOL, "log"),
    (SIGNOZ_METRICS_TOOL, "metric"),
]
MAX_ITERATIONS = len(EVIDENCE_QUERY_PLAN)

LOOP_BREAKER_REPEAT_THRESHOLD = 3  # same query hash seen more than this many times -> stop
TOKEN_BUDGET = 20_000  # total input+output tokens per investigation (see cost-watchdog note above)
CONFIDENCE_STOP_THRESHOLD = 0.75  # stop iterating once a hypothesis is this confident

# Known incident vocabulary - matches app.flags.FLAG_NAMES exactly (Phase 3's four
# seeded scenarios), given to the LLM so it can name a scenario rather than
# inventing free-form root causes.
KNOWN_INCIDENT_TYPES = ("prompt_regression", "retry_storm", "retrieval_latency", "db_pool_exhaustion")

INVESTIGATION_SYSTEM_PROMPT = (
    "You are Agent K, an automated incident-response investigator. You are given "
    "SigNoz evidence (traces/logs/metrics) gathered for a firing alert. Identify the "
    "most likely root cause from this list of known failure scenarios: "
    f"{', '.join(KNOWN_INCIDENT_TYPES)} - or 'unknown' if the evidence does not "
    "clearly match one of these. Respond with ONLY a JSON object of the exact shape "
    '{"claim": "<one sentence root-cause claim>", "confidence": <0.0-1.0>}.'
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
    if inv.query_hash_counts[query_hash] > LOOP_BREAKER_REPEAT_THRESHOLD:
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
    inv.watchdog_events.append(
        {"kind": "cost_budget", "total_tokens": inv.total_tokens, "budget": TOKEN_BUDGET}
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.watchdog.cost_budget") as span:
        span.set_attribute(AGENTK_WATCHDOG_KIND, "cost_budget")
        span.set_attribute(AGENTK_WATCHDOG_TOTAL_TOKENS, inv.total_tokens)
        span.set_attribute(AGENTK_WATCHDOG_BUDGET, TOKEN_BUDGET)
    logger.error("cost watchdog fired: total_tokens=%d budget=%d", inv.total_tokens, TOKEN_BUDGET)


async def _gather_evidence(inv: Investigation, alert: AlertItem, iteration: int) -> list[Evidence]:
    """Issue one iteration's evidence-gathering MCP query (LAW3-02).

    Every MCP call goes through signoz_mcp.query_signoz (MCP-02's single call
    site) - this function never calls the MCP SDK directly. `iteration` selects
    the query from EVIDENCE_QUERY_PLAN, so a normal multi-iteration investigation
    never repeats a query (see module docstring).
    """
    service = alert.labels.get("service", "unknown-service")
    time_range = f"{alert.startsAt}/{alert.endsAt or 'now'}"
    tool_name, ev_type = EVIDENCE_QUERY_PLAN[iteration]
    arguments = {"service": service, "time_range": time_range}

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
    inv.last_evidence_text.append(content_text)
    return [
        Evidence(
            type=ev_type,
            query=f"{tool_name}({arguments})",
            time_range=time_range,
            link=build_evidence_link(ev_type, service, time_range),
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

    if inv.total_tokens > TOKEN_BUDGET:
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
                if hypothesis is not None and hypothesis.confidence >= CONFIDENCE_STOP_THRESHOLD:
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
