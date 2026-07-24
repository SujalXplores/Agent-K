"""Law 2 action-policy gate: the deterministic, zero-LLM allow/deny decision that
every action Agent K could take must pass through (LAW2-01/02/05/06).

THIS MODULE MUST NEVER CALL AN LLM. That is the entire point of Law 2 - the
allow/deny verdict is produced by auditable code reading numbers, not by a model
being asked nicely whether it thinks a rollback is a good idea. The constraint is
enforced structurally (this module imports no LLM client - see the deliberate
absence of `from app import llm`) and is asserted directly by
tests/test_policy.py::test_policy_module_makes_no_llm_calls, which fails the build
if `app.llm` ever appears in this module's import graph. If you find yourself
wanting model input here, the answer is to put it in the CLAIM's confidence (which
app/claims.py already recalibrates in code) and let the threshold check below read
that number - not to call a model from inside the gate.

Six checks, all must pass for an approved verdict (LAW2-01):

  1. slo_breach          - the alert's burn rate actually exceeds the configured SLO
  2. allowlist           - the requested action is in ACTION_ALLOWLIST (exactly one entry)
  3. cooldown            - no rollback executed against this target within COOLDOWN_SECONDS
  4. confidence          - the best evidence-backed claim clears CONFIDENCE_THRESHOLD
  5. deployment_related  - the diagnosed incident is a deployment-class cause
  6. sandbox_scope       - the target service is inside the permitted sandbox

Check 5 is what produces LAW2-07's required 2-approved/2-denied split across the
four seeded incidents, and it does so by reading app.flags.DEPLOYMENT_CLASS_FLAGS -
the SAME set Phase 3's FLAG-06 deployment-marker emitter uses to decide whether a
scenario gets a deployment marker at all. The split is therefore a consequence of
one shared definition of "deployment-class", not two hand-tuned lists that happen
to agree today and silently diverge later.

On ANY failed check the verdict is denied, no action is taken, and the decision
carries a human-readable recommendation plus the evidence links from the claim that
motivated it (LAW2-05) - a denial is a handoff to a human, never a dead end.

SLO-value convention (live-verification gap, consistent with Phases 2-5): the burn
rate is read from the alert's annotations/labels under the first matching key in
_BURN_RATE_KEYS. SigNoz's real alert payload's actual carrier field for a burn-rate
value is unconfirmed in this environment, so a missing value is treated as 0.0 -
which FAILS the SLO check and therefore DENIES the action. The unknown case is
deliberately fail-closed: an alert we cannot read a burn rate from must never be
able to trigger a rollback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from opentelemetry import trace

from app.claims import Claim
from app.flags import DEPLOYMENT_CLASS_FLAGS, FLAG_NAMES
from app.observability import (
    AGENTK_POLICY_ACTION,
    AGENTK_POLICY_ALLOWLIST_PASSED,
    AGENTK_POLICY_CONFIDENCE,
    AGENTK_POLICY_CONFIDENCE_PASSED,
    AGENTK_POLICY_CONFIDENCE_THRESHOLD,
    AGENTK_POLICY_COOLDOWN_PASSED,
    AGENTK_POLICY_DEPLOYMENT_RELATED_PASSED,
    AGENTK_POLICY_FAILED_CHECKS,
    AGENTK_POLICY_INCIDENT_ID,
    AGENTK_POLICY_REASON,
    AGENTK_POLICY_SANDBOX_PASSED,
    AGENTK_POLICY_SLO_PASSED,
    AGENTK_POLICY_SLO_THRESHOLD,
    AGENTK_POLICY_SLO_VALUE,
    AGENTK_POLICY_VERDICT,
)

if TYPE_CHECKING:
    from app.alerts_webhook import AlertItem

logger = logging.getLogger(__name__)

# --- Locked policy constants ---

ROLLBACK_ACTION = "rollback"

# LAW2-02: the action allowlist contains EXACTLY ONE action. This is asserted by
# tests/test_policy.py::test_allowlist_contains_exactly_one_action - adding a
# second entry is a deliberate, test-breaking act, not an accident.
ACTION_ALLOWLIST: tuple[str, ...] = (ROLLBACK_ACTION,)

# The only service Agent K may act on (check 6, sandbox scope). Matches
# app/telemetry.py's DEFAULT_SERVICE_NAME - the one monitored RAG app.
SANDBOX_SERVICES: frozenset[str] = frozenset({"agent-k-rag-service"})

BURN_RATE_THRESHOLD = 1.0  # burn rate > 1.0 means the error budget is being consumed too fast
CONFIDENCE_THRESHOLD = 0.70  # a claim must be at least this confident to justify acting
COOLDOWN_SECONDS = 600.0  # no second rollback against the same target within 10 minutes

# Annotation/label keys the burn rate may arrive under, in priority order.
# See the SLO-value convention note in the module docstring.
_BURN_RATE_KEYS = ("burn_rate", "slo_burn_rate", "burnRate", "value")


@dataclass(frozen=True)
class PolicyCheck:
    """One individual gate's outcome, kept for the audit trail (LAW2-06)."""

    name: str
    passed: bool
    detail: str


@dataclass
class PolicyDecision:
    """The full record of one allow/deny decision (LAW2-06).

    Carries every field the requirement enumerates, so the span stamped from it
    and the Phase 7 Action Audit Trail rendering both read from one object rather
    than re-deriving anything.
    """

    action: str
    incident_id: str
    verdict: str  # "approved" | "denied"
    reason: str
    checks: list[PolicyCheck] = field(default_factory=list)
    slo_value: float = 0.0
    slo_threshold: float = BURN_RATE_THRESHOLD
    confidence: float = 0.0
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    target_service: str = ""
    incident_type: str | None = None
    recommendation: str | None = None
    evidence_links: list[str] = field(default_factory=list)

    @property
    def approved(self) -> bool:
        return self.verdict == "approved"

    @property
    def failed_checks(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]


# --- Cooldown ledger (check 3) ---
# Module-level, in-process, keyed by target service - mirrors app/flags.py's
# in-memory store decision. Resets on process start, which is fail-OPEN for the
# very first action after a restart; acceptable because a restart is an operator
# action, and the alternative (persisting cooldown state) is out of scope for a
# 7-day build. Documented rather than silently assumed.
_last_action_at: dict[str, float] = {}


def record_action_executed(target_service: str, *, now: float | None = None) -> None:
    """Stamp the cooldown ledger after an action actually executes.

    Called by app/rollback.py ONLY on a real execution - never on a denied verdict
    or a failed call, so a failure can be retried without waiting out a cooldown
    that never protected anything.
    """
    _last_action_at[target_service] = time.monotonic() if now is None else now


def clear_cooldowns() -> None:
    """Reset the cooldown ledger (test-support / demo reset)."""
    _last_action_at.clear()


def seconds_since_last_action(target_service: str, *, now: float | None = None) -> float | None:
    """Seconds since the last executed action against `target_service`, or None."""
    last = _last_action_at.get(target_service)
    if last is None:
        return None
    return (time.monotonic() if now is None else now) - last


# --- Individual checks ---


def extract_burn_rate(alert: AlertItem) -> float:
    """Read the alert's burn rate, fail-closed to 0.0 when absent/unparseable.

    Fail-closed matters: 0.0 fails the SLO check, so an alert whose burn rate we
    cannot read can never approve an action (see module docstring).
    """
    source = {**alert.labels, **alert.annotations}
    for key in _BURN_RATE_KEYS:
        raw = source.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            logger.warning("burn rate under key %r was not parseable as a float", key)
            continue
    return 0.0


def infer_incident_type(claims: list[Claim], alert: AlertItem) -> str | None:
    """Determine which seeded scenario the evidence points at (check 5's input).

    Prefers the highest-confidence claim's text, since app/investigation.py's
    prompt constrains the model to name one of the known scenarios verbatim;
    falls back to the alert's own `scenario`/`alertname` labels. Returns None
    when nothing matches - which FAILS the deployment-related check, keeping the
    unknown case fail-closed like every other unknown here.
    """
    for claim in sorted(claims, key=lambda c: c.confidence, reverse=True):
        haystack = claim.claim.lower()
        for name in FLAG_NAMES:
            if name in haystack:
                return name

    for label_key in ("scenario", "alertname"):
        raw = alert.labels.get(label_key, "").lower()
        for name in FLAG_NAMES:
            if name in raw:
                return name

    return None


def best_claim(claims: list[Claim]) -> Claim | None:
    """The highest-confidence evidence-backed claim, or None.

    Claims with empty evidence are excluded here as well as in the report
    renderer (LAW1-02) - an unevidenced claim must not be able to justify an
    ACTION either, not just be barred from being displayed.
    """
    evidenced = [c for c in claims if c.evidence]
    if not evidenced:
        return None
    return max(evidenced, key=lambda c: c.confidence)


def _build_recommendation(action: str, failed: list[PolicyCheck], incident_type: str | None) -> str:
    """Human-facing next-step text for a denied verdict (LAW2-05)."""
    reasons = "; ".join(f"{c.name}: {c.detail}" for c in failed)
    scenario = incident_type or "an undetermined scenario"
    return (
        f"Agent K did NOT execute {action}. Diagnosed {scenario}, but the policy gate "
        f"denied the action because — {reasons}. A human should review the linked "
        f"evidence and decide whether to intervene manually."
    )


def evaluate_policy(
    *,
    action: str,
    incident_id: str,
    alert: AlertItem,
    claims: list[Claim],
    now: float | None = None,
) -> PolicyDecision:
    """Run all six checks and return the allow/deny decision (LAW2-01/02/05).

    Zero LLM calls - see the module docstring. Emits the `agentk.policy.decision`
    span carrying every field LAW2-06 enumerates, for BOTH verdicts: a denial is
    recorded exactly as thoroughly as an approval, which is what makes the Phase 7
    Action Audit Trail able to give denied verdicts equal prominence (DASH-04).
    """
    target_service = alert.labels.get("service", "")
    winning_claim = best_claim(claims)
    confidence = winning_claim.confidence if winning_claim else 0.0
    burn_rate = extract_burn_rate(alert)
    incident_type = infer_incident_type(claims, alert)

    checks: list[PolicyCheck] = []

    # 1. SLO / burn-rate breach
    slo_ok = burn_rate > BURN_RATE_THRESHOLD
    checks.append(
        PolicyCheck(
            "slo_breach",
            slo_ok,
            f"burn rate {burn_rate:.3f} vs threshold {BURN_RATE_THRESHOLD:.3f}",
        )
    )

    # 2. Allowlist membership (LAW2-02)
    allowlist_ok = action in ACTION_ALLOWLIST
    checks.append(
        PolicyCheck(
            "allowlist",
            allowlist_ok,
            f"{action!r} {'is' if allowlist_ok else 'is NOT'} in allowlist {list(ACTION_ALLOWLIST)}",
        )
    )

    # 3. Cooldown
    elapsed = seconds_since_last_action(target_service, now=now)
    cooldown_ok = elapsed is None or elapsed >= COOLDOWN_SECONDS
    checks.append(
        PolicyCheck(
            "cooldown",
            cooldown_ok,
            "no prior action recorded"
            if elapsed is None
            else f"{elapsed:.1f}s since last action vs {COOLDOWN_SECONDS:.1f}s cooldown",
        )
    )

    # 4. Confidence threshold
    confidence_ok = confidence >= CONFIDENCE_THRESHOLD
    checks.append(
        PolicyCheck(
            "confidence",
            confidence_ok,
            f"best evidenced claim confidence {confidence:.3f} vs threshold {CONFIDENCE_THRESHOLD:.3f}",
        )
    )

    # 5. Deployment-related cause (produces LAW2-07's 2/2 split)
    deployment_ok = incident_type in DEPLOYMENT_CLASS_FLAGS
    checks.append(
        PolicyCheck(
            "deployment_related",
            deployment_ok,
            f"incident type {incident_type!r} "
            f"{'is' if deployment_ok else 'is NOT'} deployment-class "
            f"{sorted(DEPLOYMENT_CLASS_FLAGS)}",
        )
    )

    # 6. Sandbox scope
    sandbox_ok = target_service in SANDBOX_SERVICES
    checks.append(
        PolicyCheck(
            "sandbox_scope",
            sandbox_ok,
            f"target {target_service!r} "
            f"{'is' if sandbox_ok else 'is NOT'} within sandbox {sorted(SANDBOX_SERVICES)}",
        )
    )

    failed = [c for c in checks if not c.passed]
    approved = not failed

    decision = PolicyDecision(
        action=action,
        incident_id=incident_id,
        verdict="approved" if approved else "denied",
        reason="all policy checks passed"
        if approved
        else "; ".join(f"{c.name} failed ({c.detail})" for c in failed),
        checks=checks,
        slo_value=burn_rate,
        confidence=confidence,
        target_service=target_service,
        incident_type=incident_type,
        evidence_links=[e.link for e in winning_claim.evidence] if winning_claim else [],
    )

    if not approved:
        # LAW2-05: a denial always hands a human something actionable.
        decision.recommendation = _build_recommendation(action, failed, incident_type)

    _record_decision_span(decision)

    logger.info(
        "policy decision: action=%s incident=%s verdict=%s failed_checks=%s",
        action,
        incident_id,
        decision.verdict,
        decision.failed_checks,
    )
    return decision


def _record_decision_span(decision: PolicyDecision) -> None:
    """Stamp the full decision onto an `agentk.policy.decision` span (LAW2-06).

    Tracer acquired fresh (never cached at import) so tests' monkeypatched
    in-memory provider is observed - the established app/rag.py, app/llm.py,
    app/flags.py convention.
    """
    by_name = {c.name: c.passed for c in decision.checks}
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agentk.policy.decision") as span:
        span.set_attribute(AGENTK_POLICY_ACTION, decision.action)
        span.set_attribute(AGENTK_POLICY_INCIDENT_ID, decision.incident_id)
        span.set_attribute(AGENTK_POLICY_SLO_VALUE, decision.slo_value)
        span.set_attribute(AGENTK_POLICY_SLO_THRESHOLD, decision.slo_threshold)
        span.set_attribute(AGENTK_POLICY_CONFIDENCE, decision.confidence)
        span.set_attribute(AGENTK_POLICY_CONFIDENCE_THRESHOLD, decision.confidence_threshold)
        span.set_attribute(AGENTK_POLICY_SLO_PASSED, by_name.get("slo_breach", False))
        span.set_attribute(AGENTK_POLICY_ALLOWLIST_PASSED, by_name.get("allowlist", False))
        span.set_attribute(AGENTK_POLICY_COOLDOWN_PASSED, by_name.get("cooldown", False))
        span.set_attribute(AGENTK_POLICY_CONFIDENCE_PASSED, by_name.get("confidence", False))
        span.set_attribute(
            AGENTK_POLICY_DEPLOYMENT_RELATED_PASSED, by_name.get("deployment_related", False)
        )
        span.set_attribute(AGENTK_POLICY_SANDBOX_PASSED, by_name.get("sandbox_scope", False))
        span.set_attribute(AGENTK_POLICY_VERDICT, decision.verdict)
        span.set_attribute(AGENTK_POLICY_REASON, decision.reason)
        span.set_attribute(AGENTK_POLICY_FAILED_CHECKS, ",".join(decision.failed_checks))
