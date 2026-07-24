"""The human-facing incident report page (REPT-01/02/03).

This is where everything the previous six phases enforced becomes legible to a
person: the evidence-backed claims (Law 1), the six-check policy verdict and what
Agent K did or refused to do (Law 2), and the agent's own cost/behaviour numbers
(Law 3) - all on one page, addressable by incident ID.

THE REPORT PAGE IS THE PUBLICATION BOUNDARY. app/claims.py describes
strip_unevidenced_claims() as "the report-renderer-side backstop", and this module
is that renderer - so it applies the filter again here rather than trusting that
app/investigation.py already did. Publishing is the moment LAW1-02 actually has to
hold, and it now holds at the moment of publication regardless of what any upstream
code did or forgot to do. tests/test_report.py asserts this directly by injecting an
unevidenced claim into a stored investigation and confirming it never reaches HTML.

A DENIED VERDICT IS A FIRST-CLASS OUTCOME, NOT AN ERROR, and is rendered with the
same prominence as an executed action (the disposition DASH-04 asks for). Agent K
correctly declining to act is the product working, so denials are styled
informational rather than red-alarming - the failure mode this page exists to
prevent is a human skimming it and reading "denied" as "broken".

Honesty rules baked into the rendering, mirroring app/rollback.py's own discipline:
an executed rollback whose recovery could NOT be verified is never shown as a
success - it gets its own distinct warning treatment, because "compose reported
success" is not "the incident is over". Likewise an investigation stopped early by
the loop breaker or cost watchdog renders as an explicit needs-human state (REPT-03)
rather than as a weakly-worded conclusion drawn from evidence Agent K never
finished gathering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import investigation as investigation_module
from app.claims import Claim, strip_unevidenced_claims
from app.investigation import Investigation
from app.policy import PolicyDecision
from app.rollback import ActionOutcome

router = APIRouter()

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

# --- Report status vocabulary -------------------------------------------------
# Derived from the investigation record in one place (derive_status) so the index
# and the detail page can never disagree about what happened in an incident.

STATUS_NEEDS_HUMAN = "needs_human"
STATUS_ACTION_DENIED = "action_denied"
STATUS_ACTION_EXECUTED = "action_executed"
STATUS_ACTION_FAILED = "action_failed"
STATUS_NO_DECISION = "no_decision"

STATUS_LABELS: dict[str, str] = {
    STATUS_NEEDS_HUMAN: "Needs human",
    STATUS_ACTION_DENIED: "Action denied by policy",
    STATUS_ACTION_EXECUTED: "Rollback executed",
    STATUS_ACTION_FAILED: "Action attempted, did not complete",
    STATUS_NO_DECISION: "No policy decision recorded",
}

# Visual tone per outcome. Note STATUS_ACTION_DENIED maps to "info", never
# "danger": the gate refusing an action is the safety system working as designed,
# and colouring it like a failure would actively misrepresent the result.
TONE_OK = "ok"
TONE_WARN = "warn"
TONE_INFO = "info"
TONE_DANGER = "danger"
TONE_NEUTRAL = "neutral"


@dataclass(frozen=True)
class ReportView:
    """Everything one report page renders, resolved from an Investigation.

    A flat, pre-computed view model: all filtering, sorting and status derivation
    happens here in testable Python, leaving the templates free of logic that
    could silently drift between the index and the detail page.
    """

    id: str
    state: str
    status: str
    status_label: str
    status_detail: str
    tone: str
    needs_human: bool
    escalation_reason: str | None
    alertname: str
    service: str
    started_at: str
    claims: list[Claim]
    decision: PolicyDecision | None
    outcome: ActionOutcome | None
    mcp_query_count: int
    mcp_query_failures: int
    total_tokens: int
    duration_s: float | None
    watchdog_events: list[dict]

    @property
    def top_claim(self) -> Claim | None:
        """The claim a human should read first, or None if there is nothing to publish."""
        return self.claims[0] if self.claims else None


def derive_status(inv: Investigation) -> str:
    """Classify one investigation's outcome (the single source of truth for status).

    Order matters. `incomplete` is checked FIRST because an investigation stopped
    early by a watchdog never reached the act stage at all - reporting anything
    about a policy verdict for it would be reporting on a decision that was never
    made (REPT-03).
    """
    if inv.incomplete:
        return STATUS_NEEDS_HUMAN

    decision = inv.policy_decision
    if decision is None:
        return STATUS_NO_DECISION
    if not decision.approved:
        return STATUS_ACTION_DENIED

    outcome = inv.action_outcome
    if outcome is not None and outcome.executed:
        return STATUS_ACTION_EXECUTED
    # Approved but not executed: the sidecar returned a conflict/error, or the act
    # stage crashed after the gate passed. Either way an action was authorised and
    # did not land, which a human needs to see as distinct from a clean denial.
    return STATUS_ACTION_FAILED


def derive_tone(status: str, outcome: ActionOutcome | None) -> str:
    """Map a status to its visual treatment.

    An EXECUTED rollback is only "ok" when SigNoz actually confirmed recovery.
    Executed-but-unverified is a warning, because app/rollback.py deliberately
    refuses to claim a recovery it could not demonstrate and this page must not
    quietly upgrade that into a success.
    """
    if status == STATUS_ACTION_EXECUTED:
        return TONE_OK if (outcome is not None and outcome.verified) else TONE_WARN
    if status == STATUS_ACTION_DENIED:
        return TONE_INFO
    if status == STATUS_ACTION_FAILED:
        return TONE_DANGER
    if status == STATUS_NEEDS_HUMAN:
        return TONE_WARN
    return TONE_NEUTRAL


def escalation_reason(inv: Investigation) -> str | None:
    """Plain-language explanation of why an incomplete investigation stopped (REPT-03).

    Returns None for a complete investigation. Passive escalation only - this text
    is the entire handoff, no notification channel is built (per the locked scope).
    """
    if not inv.incomplete:
        return None

    events = {event.get("kind"): event for event in inv.watchdog_events}

    if inv.loop_breaker_fired:
        event = events.get("loop_breaker", {})
        repeats = event.get("repeat_count", "several")
        return (
            f"The loop breaker stopped this investigation: Agent K issued the same "
            f"SigNoz query {repeats} times without making progress. The partial "
            f"evidence below is everything it gathered before stopping."
        )

    if inv.cost_watchdog_fired:
        event = events.get("cost_budget", {})
        used = event.get("total_tokens", inv.total_tokens)
        budget = event.get("budget", "the budget")
        return (
            f"The cost watchdog stopped this investigation: it consumed {used} tokens "
            f"against a budget of {budget}. The partial evidence below is everything "
            f"it gathered before stopping."
        )

    if not inv.claims:
        return (
            "Agent K could not form a single evidence-backed claim about this "
            "incident. Rather than publish a guess, it is handing the incident over "
            "with nothing asserted."
        )

    return (
        "This investigation ended unexpectedly before reaching a conclusion. Treat "
        "anything below as partial."
    )


def _status_detail(
    status: str,
    inv: Investigation,
    decision: PolicyDecision | None,
    outcome: ActionOutcome | None,
) -> str:
    """One-line summary shown in the status banner, beneath the label."""
    if status == STATUS_NEEDS_HUMAN:
        return escalation_reason(inv) or "This investigation did not complete."

    if status == STATUS_ACTION_DENIED and decision is not None:
        failed = ", ".join(decision.failed_checks)
        return (
            f"Agent K diagnosed this incident but took no action. "
            f"Policy check(s) not satisfied: {failed}."
        )

    if status == STATUS_ACTION_EXECUTED and outcome is not None:
        if outcome.verified:
            return f"Rollback executed and recovery confirmed in SigNoz — {outcome.verification_detail}"
        return (
            "Rollback executed, but recovery could NOT be verified in SigNoz — "
            f"{outcome.verification_detail}. Do not assume the incident is resolved."
        )

    if status == STATUS_ACTION_FAILED:
        if outcome is None:
            return (
                "The policy gate approved this action but no outcome was recorded. "
                "The action stage did not complete."
            )
        return (
            f"The policy gate approved this action but it did not complete "
            f"(status: {outcome.status}). No recovery has been verified."
        )

    return (
        "This investigation completed but no policy decision was recorded against it."
    )


def build_report_view(inv: Investigation) -> ReportView:
    """Resolve one Investigation into its rendered form.

    LAW1-02 is enforced here at the publication boundary: unevidenced claims are
    stripped before anything is handed to a template, so no code path - present or
    future - can put an unsupported claim in front of a human. Remaining claims are
    ordered by confidence so the strongest hypothesis is what gets read first.
    """
    claims = sorted(strip_unevidenced_claims(inv.claims), key=lambda c: c.confidence, reverse=True)

    status = derive_status(inv)
    decision = inv.policy_decision
    outcome = inv.action_outcome

    # A needs-human investigation reports NO verdict, even if the record somehow
    # carries one. _run_act_stage already guarantees it cannot (an incomplete
    # investigation never reaches the act stage), but the page must not depend on
    # an upstream invariant it has no way to enforce - the same reason claims are
    # re-stripped above. Without this, a self-contradictory record would render a
    # "Needs human" banner directly above a full approved-verdict table, and a
    # human skimming it would take away the opposite of what happened.
    if status == STATUS_NEEDS_HUMAN:
        decision = None
        outcome = None

    return ReportView(
        id=inv.id,
        state=inv.state.value,
        status=status,
        status_label=STATUS_LABELS[status],
        status_detail=_status_detail(status, inv, decision, outcome),
        tone=derive_tone(status, outcome),
        needs_human=inv.incomplete,
        escalation_reason=escalation_reason(inv),
        alertname=inv.alert.labels.get("alertname", "unknown"),
        service=inv.alert.labels.get("service", "unknown"),
        started_at=inv.alert.startsAt,
        claims=claims,
        decision=decision,
        outcome=outcome,
        mcp_query_count=inv.mcp_query_count,
        mcp_query_failures=inv.mcp_query_failures,
        total_tokens=inv.total_tokens,
        duration_s=inv.duration_s,
        watchdog_events=inv.watchdog_events,
    )


def build_index_views() -> list[ReportView]:
    """Every investigation, newest first (REPT-02).

    Ordered by the monotonic start clock rather than the alert's own timestamp, so
    the list reflects the order Agent K actually worked the incidents even if two
    alerts carry the same or out-of-order `startsAt`.
    """
    investigations = sorted(
        investigation_module.list_investigations(),
        key=lambda i: i.started_at,
        reverse=True,
    )
    return [build_report_view(inv) for inv in investigations]


@router.get("/report", response_class=HTMLResponse)
async def report_index(request: Request):
    """Browsable list of past investigations (REPT-02)."""
    views = build_index_views()
    counts = {
        "total": len(views),
        "executed": sum(1 for v in views if v.status == STATUS_ACTION_EXECUTED),
        "denied": sum(1 for v in views if v.status == STATUS_ACTION_DENIED),
        "needs_human": sum(1 for v in views if v.status == STATUS_NEEDS_HUMAN),
    }
    return templates.TemplateResponse(
        request=request,
        name="report_index.html",
        context={"views": views, "counts": counts},
    )


@router.get("/report/{investigation_id}", response_class=HTMLResponse)
async def report_detail(investigation_id: str, request: Request):
    """One investigation's full RCA, addressable by incident ID (REPT-01/02)."""
    inv = investigation_module.get_investigation(investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="unknown investigation id")
    return templates.TemplateResponse(
        request=request,
        name="report_detail.html",
        context={"view": build_report_view(inv)},
    )
