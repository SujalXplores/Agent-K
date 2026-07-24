"""Agent K's action executor: the one authenticated call to the deployer sidecar,
plus the independent recovery verification that follows it (LAW2-03/04).

This module is Agent K's ENTIRE capability to change the world. It holds no Docker
socket, builds no command line, and names no image - it makes one authenticated
HTTP POST to the sidecar's single endpoint with an empty body and reads back what
the sidecar decided to do. Everything about how a rollback is performed lives on
the other side of that boundary, in deployer/main.py.

Verification (LAW2-04) is deliberately SEPARATE from execution and fails closed. A
2xx from the sidecar means "compose reported success", which is not the same as
"the incident is over" - so after a wait, Agent K re-queries SigNoz through the
Phase-4 MCP wrapper and only records `verified=True` when it can actually read a
recovered error rate back. If the evidence is unreadable, unparseable, or missing,
the outcome is recorded as UNVERIFIED, never as recovered. Claiming a recovery
Agent K cannot demonstrate would violate the same core value Law 1 enforces for
claims: nothing is trust-me, everything is prove-it-in-telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx
from opentelemetry import trace

from app import policy as policy_module
from app import signoz_mcp
from app.observability import (
    AGENTK_ACTION_HTTP_STATUS,
    AGENTK_ACTION_KIND,
    AGENTK_ACTION_PREVIOUS_IMAGE,
    AGENTK_ACTION_STATUS,
    AGENTK_ACTION_VERIFICATION_DETAIL,
    AGENTK_ACTION_VERIFIED,
)

logger = logging.getLogger(__name__)

DEFAULT_DEPLOYER_URL = "http://deployer:9000"
ROLLBACK_HTTP_TIMEOUT_S = 200.0  # must exceed the sidecar's own 180s compose timeout
VERIFICATION_WAIT_S = 30.0  # let the recreated service emit post-rollback telemetry
RECOVERED_ERROR_RATE_MAX = 0.05  # error ratio at/below this counts as recovered

# Verified against signoz-mcp-server v0.9.0's tool list on 2026-07-25. This was
# "query_metrics", which does not exist; the real signoz_query_metrics also requires
# a `metricName` this app never emits (no custom metrics, only auto-instrumented
# spans), so recovery is measured by counting spans grouped by has_error instead.
RECOVERY_TOOL = "signoz_aggregate_traces"

# Deliberately a SHORT RELATIVE window, not the incident's window: the question
# after a rollback is "is the service healthy NOW", and re-querying the original
# incident range would re-read the very error spans the rollback was meant to stop
# and conclude nothing had changed.
RECOVERY_TIME_RANGE = "5m"

# Back-compat: an "error_rate: 0.02"-style payload.
_ERROR_RATE_PATTERN = re.compile(r"error[_\s]?rate\D{0,10}([0-9]*\.?[0-9]+)", re.IGNORECASE)

# has_error-grouped span counts, e.g. `"has_error": "true" ... "count": 3`.
_HAS_ERROR_GROUP_PATTERN = re.compile(
    r'has_error"?\s*[:=]\s*"?(true|false)"?[^}]*?(\d+(?:\.\d+)?)', re.IGNORECASE
)


@dataclass
class ActionOutcome:
    """What Agent K actually did, and whether SigNoz confirmed it worked."""

    kind: str
    status: str  # "executed" | "failed" | "conflict" | "skipped"
    http_status: int | None = None
    previous_image: str | None = None
    rolled_back_to: str | None = None
    verified: bool = False
    verification_detail: str = "not attempted"

    @property
    def executed(self) -> bool:
        return self.status == "executed"


async def _call_deployer() -> httpx.Response:
    """POST /rollback with an empty body and the shared token (LAW2-03).

    No image reference, no service name, no command - the sidecar owns all of
    that. This function is the complete inventory of what Agent K can ask for.
    """
    base = os.getenv("DEPLOYER_URL", DEFAULT_DEPLOYER_URL).rstrip("/")
    token = os.getenv("DEPLOYER_TOKEN", "")
    async with httpx.AsyncClient(timeout=ROLLBACK_HTTP_TIMEOUT_S) as client:
        return await client.post(f"{base}/rollback", headers={"X-Deployer-Token": token})


def _parse_error_rate(text: str) -> float | None:
    """Read an error RATIO in [0,1] out of a recovery-query payload, or None.

    Two accepted shapes, in order: an explicit "error_rate: 0.02", or has_error-
    grouped span counts which are divided into a ratio here. Returns None - never
    a guess - when neither is present, because verify_recovery treats None as
    UNVERIFIED, and inventing a number would be the one thing Law 2's verification
    step exists to prevent.
    """
    match = _ERROR_RATE_PATTERN.search(text)
    if match is not None:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    counts: dict[str, float] = {}
    for flag, value in _HAS_ERROR_GROUP_PATTERN.findall(text):
        try:
            counts[flag.lower()] = counts.get(flag.lower(), 0.0) + float(value)
        except ValueError:
            continue

    total = counts.get("true", 0.0) + counts.get("false", 0.0)
    if total <= 0:
        return None
    return counts.get("true", 0.0) / total


async def verify_recovery(service: str, time_range: str) -> tuple[bool, str]:
    """Re-query SigNoz and decide whether the service actually recovered (LAW2-04).

    Returns (verified, detail). Every failure mode - query exception, tool-reported
    error, unparseable payload - returns False with a detail explaining why, so an
    unverifiable rollback is always distinguishable from a verified-failed one in
    the report and the audit trail.
    """
    try:
        result = await signoz_mcp.query_signoz(
            RECOVERY_TOOL,
            {
                "aggregation": "count",
                "groupBy": "has_error",
                "service": service,
                "timeRange": RECOVERY_TIME_RANGE,
            },
        )
    except Exception:
        logger.exception("recovery verification query failed")
        return False, "verification query raised an exception"

    if result.isError:
        return False, "verification query returned an error result"

    text = "\n".join(getattr(block, "text", "") for block in result.content)
    error_rate = _parse_error_rate(text)
    if error_rate is None:
        return False, "could not parse an error rate from the verification query"

    if error_rate <= RECOVERED_ERROR_RATE_MAX:
        return True, f"error rate {error_rate:.4f} <= {RECOVERED_ERROR_RATE_MAX:.4f}"
    return False, f"error rate {error_rate:.4f} still above {RECOVERED_ERROR_RATE_MAX:.4f}"


async def execute_rollback(
    *,
    decision: policy_module.PolicyDecision,
    time_range: str,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> ActionOutcome:
    """Execute an APPROVED rollback and verify it (LAW2-03/04).

    Refuses outright if handed a denied decision - the policy gate is the only
    thing that can authorize an action, and this second check means a future
    caller that forgets to test `decision.approved` still cannot act. That
    redundancy is deliberate: it is the difference between "we call the gate" and
    "the gate cannot be bypassed".

    `sleep` is injectable purely so tests need not wait out VERIFICATION_WAIT_S.
    """
    if not decision.approved:
        logger.warning("refusing to execute a denied decision for incident %s", decision.incident_id)
        return ActionOutcome(
            kind=decision.action,
            status="skipped",
            verification_detail="policy denied; no action attempted",
        )

    sleep_fn = sleep or asyncio.sleep
    outcome = ActionOutcome(kind=decision.action, status="failed")

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.action.rollback") as span:
        try:
            response = await _call_deployer()
            outcome.http_status = response.status_code
        except Exception:
            logger.exception("deployer call failed")
            outcome.verification_detail = "deployer call raised an exception"
            _stamp(span, outcome)
            return outcome

        if response.status_code == 409:
            outcome.status = "conflict"
            outcome.verification_detail = "a rollback was already in flight"
            _stamp(span, outcome)
            return outcome

        if response.status_code >= 400:
            outcome.verification_detail = f"deployer returned HTTP {response.status_code}"
            _stamp(span, outcome)
            return outcome

        body = response.json()
        outcome.status = "executed"
        outcome.previous_image = body.get("previous_image")
        outcome.rolled_back_to = body.get("rolled_back_to")

        # Cooldown starts at real execution only, never at a denial or a failure
        # (see app/policy.py's record_action_executed).
        policy_module.record_action_executed(decision.target_service)

        await sleep_fn(VERIFICATION_WAIT_S)
        outcome.verified, outcome.verification_detail = await verify_recovery(
            decision.target_service, time_range
        )

        _stamp(span, outcome)

    logger.info(
        "rollback outcome: status=%s verified=%s detail=%s",
        outcome.status,
        outcome.verified,
        outcome.verification_detail,
    )
    return outcome


def _stamp(span: trace.Span, outcome: ActionOutcome) -> None:
    span.set_attribute(AGENTK_ACTION_KIND, outcome.kind)
    span.set_attribute(AGENTK_ACTION_STATUS, outcome.status)
    span.set_attribute(AGENTK_ACTION_VERIFIED, outcome.verified)
    span.set_attribute(AGENTK_ACTION_VERIFICATION_DETAIL, outcome.verification_detail)
    if outcome.http_status is not None:
        span.set_attribute(AGENTK_ACTION_HTTP_STATUS, outcome.http_status)
    if outcome.previous_image is not None:
        span.set_attribute(AGENTK_ACTION_PREVIOUS_IMAGE, outcome.previous_image)
