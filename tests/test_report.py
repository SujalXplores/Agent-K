"""Tests for app.report: the incident report page's view model, status derivation,
and both routes (REPT-01/02/03).

No live SigNoz, LLM provider, or database is required - investigations are built
directly and inserted into the in-process store, which is exactly what the report
page reads from in production.

The load-bearing test in this file is
test_unevidenced_claim_never_reaches_the_rendered_page: the report page is the
publication boundary, so LAW1-02 has to hold HERE, at the moment of publication,
independently of app/investigation.py having already stripped the same claim.
"""

from __future__ import annotations

import pytest

from app import investigation as inv_module
from app import report as report_module
from app.alerts_webhook import AlertItem
from app.claims import Claim, Evidence
from app.investigation import Investigation, InvestigationState
from app.policy import PolicyCheck, PolicyDecision
from app.rollback import ActionOutcome


@pytest.fixture(autouse=True)
def _clear_investigations():
    inv_module.clear_investigations()
    yield
    inv_module.clear_investigations()


# --- builders ---


def _alert(labels=None, annotations=None) -> AlertItem:
    return AlertItem(
        status="firing",
        labels={
            "alertname": "HighErrorRate",
            "service": "agent-k-rag-service",
            **(labels or {}),
        },
        annotations=annotations or {},
        startsAt="2026-07-25T10:00:00Z",
        fingerprint="abc123",
    )


def _evidence(link: str = "http://localhost:8080/trace/abc123") -> Evidence:
    return Evidence(
        type="trace",
        query="query_traces({'service': 'agent-k-rag-service'})",
        time_range="2026-07-25T10:00:00Z/now",
        link=link,
    )


def _claim(text: str = "prompt_regression caused the error spike", confidence: float = 0.85,
           evidence: list[Evidence] | None = None) -> Claim:
    return Claim(
        claim=text,
        confidence=confidence,
        evidence=[_evidence()] if evidence is None else evidence,
    )


def _decision(approved: bool = True, **overrides) -> PolicyDecision:
    checks = [
        PolicyCheck("slo_breach", True, "burn rate 2.400 vs threshold 1.000"),
        PolicyCheck("allowlist", True, "'rollback' is in allowlist ['rollback']"),
        PolicyCheck("cooldown", True, "no prior action recorded"),
        PolicyCheck("confidence", approved, "best evidenced claim confidence 0.850 vs threshold 0.700"),
        PolicyCheck("deployment_related", True, "incident type 'prompt_regression' is deployment-class"),
        PolicyCheck("sandbox_scope", True, "target is within sandbox"),
    ]
    if not approved:
        checks[3] = PolicyCheck("confidence", False, "confidence 0.400 vs threshold 0.700")
    fields = {
        "action": "rollback",
        "incident_id": "inv-1",
        "verdict": "approved" if approved else "denied",
        "reason": "all policy checks passed" if approved else "confidence failed",
        "checks": checks,
        "slo_value": 2.4,
        "confidence": 0.85 if approved else 0.4,
        "target_service": "agent-k-rag-service",
        "incident_type": "prompt_regression",
        "evidence_links": ["http://localhost:8080/trace/abc123"],
    }
    fields.update(overrides)
    if not approved and "recommendation" not in overrides:
        fields["recommendation"] = "Agent K did NOT execute rollback. A human should review."
    return PolicyDecision(**fields)


def _investigation(
    *,
    inv_id: str = "inv-1",
    state: InvestigationState = InvestigationState.REPORTED,
    claims: list[Claim] | None = None,
    incomplete: bool = False,
    decision: PolicyDecision | None = None,
    outcome: ActionOutcome | None = None,
    store: bool = True,
    **overrides,
) -> Investigation:
    inv = Investigation(id=inv_id, alert=_alert())
    inv.state = state
    inv.claims = [_claim()] if claims is None else claims
    inv.incomplete = incomplete
    inv.policy_decision = decision
    inv.action_outcome = outcome
    inv.mcp_query_count = 3
    inv.total_tokens = 1200
    inv.duration_s = 4.25
    for key, value in overrides.items():
        setattr(inv, key, value)
    if store:
        inv_module._investigations[inv.id] = inv
    return inv


# --- derive_status ---


def test_incomplete_investigation_is_needs_human_even_with_a_decision():
    """`incomplete` is checked first: a watchdog-stopped investigation never
    reached the act stage, so no verdict should be reported for it."""
    inv = _investigation(incomplete=True, decision=_decision(approved=True), store=False)
    assert report_module.derive_status(inv) == report_module.STATUS_NEEDS_HUMAN


def test_denied_decision_is_action_denied():
    inv = _investigation(decision=_decision(approved=False), store=False)
    assert report_module.derive_status(inv) == report_module.STATUS_ACTION_DENIED


def test_approved_and_executed_is_action_executed():
    inv = _investigation(
        decision=_decision(approved=True),
        outcome=ActionOutcome(kind="rollback", status="executed", verified=True),
        store=False,
    )
    assert report_module.derive_status(inv) == report_module.STATUS_ACTION_EXECUTED


@pytest.mark.parametrize("outcome", [
    None,
    ActionOutcome(kind="rollback", status="conflict"),
    ActionOutcome(kind="rollback", status="failed"),
])
def test_approved_but_not_executed_is_action_failed(outcome):
    """An authorised action that did not land must not be indistinguishable from
    a clean denial - a human needs to know something was attempted."""
    inv = _investigation(decision=_decision(approved=True), outcome=outcome, store=False)
    assert report_module.derive_status(inv) == report_module.STATUS_ACTION_FAILED


def test_complete_investigation_without_a_decision_is_no_decision():
    inv = _investigation(decision=None, store=False)
    assert report_module.derive_status(inv) == report_module.STATUS_NO_DECISION


# --- derive_tone ---


def test_executed_and_verified_reads_as_success():
    outcome = ActionOutcome(kind="rollback", status="executed", verified=True)
    tone = report_module.derive_tone(report_module.STATUS_ACTION_EXECUTED, outcome)
    assert tone == report_module.TONE_OK


def test_executed_but_unverified_does_not_read_as_success():
    """app/rollback.py refuses to claim a recovery it cannot demonstrate; the
    report page must not quietly upgrade that into a green result."""
    outcome = ActionOutcome(kind="rollback", status="executed", verified=False)
    tone = report_module.derive_tone(report_module.STATUS_ACTION_EXECUTED, outcome)
    assert tone == report_module.TONE_WARN
    assert tone != report_module.TONE_OK


def test_denial_is_not_styled_as_a_failure():
    """A denied verdict is the safety system working, not an error (DASH-04's
    equal-prominence disposition). Styling it 'danger' would misrepresent it."""
    tone = report_module.derive_tone(report_module.STATUS_ACTION_DENIED, None)
    assert tone == report_module.TONE_INFO
    assert tone != report_module.TONE_DANGER


# --- escalation_reason (REPT-03) ---


def test_no_escalation_reason_for_a_complete_investigation():
    inv = _investigation(store=False)
    assert report_module.escalation_reason(inv) is None


def test_loop_breaker_reason_names_the_repeat_count():
    inv = _investigation(
        incomplete=True,
        loop_breaker_fired=True,
        watchdog_events=[{"kind": "loop_breaker", "query_hash": "deadbeef", "repeat_count": 4}],
        store=False,
    )
    reason = report_module.escalation_reason(inv)
    assert "loop breaker" in reason.lower()
    assert "4" in reason


def test_cost_watchdog_reason_names_tokens_and_budget():
    inv = _investigation(
        incomplete=True,
        cost_watchdog_fired=True,
        watchdog_events=[{"kind": "cost_budget", "total_tokens": 25000, "budget": 20000}],
        store=False,
    )
    reason = report_module.escalation_reason(inv)
    assert "cost watchdog" in reason.lower()
    assert "25000" in reason and "20000" in reason


def test_no_claims_reason_says_nothing_was_asserted():
    inv = _investigation(incomplete=True, claims=[], store=False)
    reason = report_module.escalation_reason(inv)
    assert "evidence-backed claim" in reason


# --- build_report_view ---


def test_claims_are_ordered_strongest_first():
    inv = _investigation(
        claims=[_claim("weak", 0.30), _claim("strong", 0.90), _claim("middling", 0.60)],
        store=False,
    )
    view = report_module.build_report_view(inv)
    assert [c.claim for c in view.claims] == ["strong", "middling", "weak"]
    assert view.top_claim.claim == "strong"


def test_view_strips_unevidenced_claims():
    inv = _investigation(
        claims=[_claim("evidenced", 0.9), _claim("bare assertion", 0.99, evidence=[])],
        store=False,
    )
    view = report_module.build_report_view(inv)
    assert [c.claim for c in view.claims] == ["evidenced"]


def test_top_claim_is_none_when_nothing_is_publishable():
    inv = _investigation(claims=[_claim("bare", 0.99, evidence=[])], store=False)
    assert report_module.build_report_view(inv).top_claim is None


# --- routes: detail (REPT-01) ---


def test_detail_page_renders_claim_evidence_and_verdict(client):
    _investigation(
        decision=_decision(approved=True),
        outcome=ActionOutcome(
            kind="rollback",
            status="executed",
            previous_image="agent-k-rag:v2-broken",
            rolled_back_to="agent-k-rag:v1-good",
            verified=True,
            verification_detail="error_rate 0.01 at or below 0.05",
        ),
    )
    response = client.get("/report/inv-1")

    assert response.status_code == 200
    body = response.text
    assert "prompt_regression caused the error spike" in body
    assert "http://localhost:8080/trace/abc123" in body  # LAW1-01 clickable deep link
    assert "85%" in body  # recalibrated confidence
    assert "agent-k-rag:v1-good" in body
    assert "Rollback executed" in body


def test_detail_page_shows_all_six_policy_checks(client):
    """The six-check table is how 'code-enforced, not trust-the-model' becomes
    inspectable rather than asserted."""
    _investigation(decision=_decision(approved=True))
    body = client.get("/report/inv-1").text
    for check in ("slo_breach", "allowlist", "cooldown", "confidence",
                  "deployment_related", "sandbox_scope"):
        assert check in body


def test_unknown_investigation_id_is_404(client):
    assert client.get("/report/does-not-exist").status_code == 404


def test_unevidenced_claim_never_reaches_the_rendered_page(client):
    """LAW1-02 enforced at the publication boundary.

    The unevidenced claim is written straight into the stored investigation,
    bypassing app/investigation.py's own strip entirely - so this passes only
    because the report renderer strips it again on the way out.
    """
    _investigation(
        claims=[
            _claim("backed by real evidence", 0.80),
            _claim("SMUGGLED UNEVIDENCED CLAIM", 0.99, evidence=[]),
        ],
        decision=_decision(approved=True),
    )
    body = client.get("/report/inv-1").text
    assert "backed by real evidence" in body
    assert "SMUGGLED UNEVIDENCED CLAIM" not in body


def test_claim_text_from_the_model_is_html_escaped(client):
    """Claim text is LLM output rendered into HTML - it must never be able to
    inject markup into the page a human reads."""
    _investigation(claims=[_claim("<script>alert('xss')</script>", 0.80)])
    body = client.get("/report/inv-1").text
    assert "<script>alert('xss')</script>" not in body
    assert "&lt;script&gt;" in body


# --- routes: denial and incomplete rendering (REPT-03, LAW2-05) ---


def test_denied_investigation_renders_verdict_and_recommendation(client):
    _investigation(decision=_decision(approved=False))
    body = client.get("/report/inv-1").text

    assert "Action denied by policy" in body
    assert "A human should review" in body
    assert "tone-info" in body      # deliberate, correct outcome
    assert "took no action" in body


def test_incomplete_investigation_renders_as_needs_human(client):
    _investigation(
        state=InvestigationState.ESCALATED,
        incomplete=True,
        loop_breaker_fired=True,
        watchdog_events=[{"kind": "loop_breaker", "query_hash": "deadbeef", "repeat_count": 4}],
    )
    body = client.get("/report/inv-1").text

    assert "Needs human" in body
    assert "Why this needs a human" in body
    assert "loop breaker" in body.lower()


def test_needs_human_page_reports_no_policy_verdict(client):
    """An investigation that never reached the act stage must not display a
    verdict, even if one was somehow attached to the record."""
    _investigation(incomplete=True, decision=_decision(approved=True))
    body = client.get("/report/inv-1").text
    assert "Needs human" in body
    assert "Policy decision (Law 2)" not in body


def test_executed_but_unverified_rollback_is_not_shown_as_recovered(client):
    _investigation(
        decision=_decision(approved=True),
        outcome=ActionOutcome(
            kind="rollback",
            status="executed",
            verified=False,
            verification_detail="no error_rate value could be read back",
        ),
    )
    body = client.get("/report/inv-1").text
    assert "NOT verified" in body
    assert "Do not assume the incident is resolved" in body


# --- routes: index (REPT-02) ---


def test_index_lists_every_investigation_with_links(client):
    _investigation(inv_id="inv-1", decision=_decision(approved=True),
                   outcome=ActionOutcome(kind="rollback", status="executed", verified=True))
    _investigation(inv_id="inv-2", decision=_decision(approved=False))
    _investigation(inv_id="inv-3", incomplete=True, claims=[])

    body = client.get("/report").text
    for inv_id in ("inv-1", "inv-2", "inv-3"):
        assert f'href="/report/{inv_id}"' in body


def test_index_counts_outcomes_by_kind(client):
    _investigation(inv_id="inv-1", decision=_decision(approved=True),
                   outcome=ActionOutcome(kind="rollback", status="executed", verified=True))
    _investigation(inv_id="inv-2", decision=_decision(approved=False))
    _investigation(inv_id="inv-3", decision=_decision(approved=False))
    _investigation(inv_id="inv-4", incomplete=True, claims=[])

    views = report_module.build_index_views()
    statuses = [v.status for v in views]
    assert statuses.count(report_module.STATUS_ACTION_EXECUTED) == 1
    assert statuses.count(report_module.STATUS_ACTION_DENIED) == 2
    assert statuses.count(report_module.STATUS_NEEDS_HUMAN) == 1


def test_index_is_ordered_newest_first(client):
    first = _investigation(inv_id="older", store=False)
    first.started_at = 100.0
    second = _investigation(inv_id="newer", store=False)
    second.started_at = 200.0
    inv_module._investigations["older"] = first
    inv_module._investigations["newer"] = second

    assert [v.id for v in report_module.build_index_views()] == ["newer", "older"]


def test_index_renders_an_empty_state_with_no_investigations(client):
    response = client.get("/report")
    assert response.status_code == 200
    assert "No investigations yet" in response.text
