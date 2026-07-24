"""Tests for app.policy: the zero-LLM Law 2 policy gate (LAW2-01/02/05/06/07).

No LLM, no SigNoz, no network - the gate is pure code reading numbers, which is
exactly the property these tests exist to hold in place.
"""

from __future__ import annotations

import pytest

from app import policy as policy_module
from app.alerts_webhook import AlertItem
from app.claims import Claim, Evidence
from app.observability import (
    AGENTK_POLICY_ACTION,
    AGENTK_POLICY_CONFIDENCE,
    AGENTK_POLICY_FAILED_CHECKS,
    AGENTK_POLICY_INCIDENT_ID,
    AGENTK_POLICY_REASON,
    AGENTK_POLICY_SLO_VALUE,
    AGENTK_POLICY_VERDICT,
)

SANDBOX_SERVICE = "agent-k-rag-service"


@pytest.fixture(autouse=True)
def _clear_cooldowns():
    policy_module.clear_cooldowns()
    yield
    policy_module.clear_cooldowns()


def _evidence(link: str = "http://localhost:8080/trace/abc") -> Evidence:
    return Evidence(
        type="trace",
        query="query_traces({'service': 'agent-k-rag-service'})",
        time_range="2026-07-25T10:00:00Z/now",
        link=link,
    )


def _claim(text: str = "prompt_regression caused the failure", confidence: float = 0.9) -> Claim:
    return Claim(claim=text, confidence=confidence, evidence=[_evidence()])


def _alert(
    *,
    service: str = SANDBOX_SERVICE,
    burn_rate: str | None = "2.5",
    labels: dict | None = None,
) -> AlertItem:
    annotations = {} if burn_rate is None else {"burn_rate": burn_rate}
    return AlertItem(
        status="firing",
        labels={"alertname": "HighErrorRate", "service": service, **(labels or {})},
        annotations=annotations,
        startsAt="2026-07-25T10:00:00Z",
        fingerprint="deadbeef",
    )


def _evaluate(**overrides):
    kwargs = {
        "action": policy_module.ROLLBACK_ACTION,
        "incident_id": "inv-1",
        "alert": _alert(),
        "claims": [_claim()],
    }
    kwargs.update(overrides)
    return policy_module.evaluate_policy(**kwargs)


# --- LAW2-02: the allowlist ---


def test_allowlist_contains_exactly_one_action():
    """LAW2-02 is a hard count, not a guideline - adding a second action must
    break the build rather than quietly widen Agent K's capabilities."""
    assert len(policy_module.ACTION_ALLOWLIST) == 1
    assert policy_module.ACTION_ALLOWLIST == ("rollback",)


def test_non_allowlisted_action_is_denied():
    decision = _evaluate(action="restart_database")
    assert not decision.approved
    assert "allowlist" in decision.failed_checks


# --- LAW2-01: zero LLM involvement ---


def test_policy_module_makes_no_llm_calls(monkeypatch):
    """The decisive Law 2 property: the verdict is produced by code, not a model.

    app.llm.generate is replaced with a function that fails the test on any call,
    then a full policy evaluation is run. This proves the absence of an LLM call
    on the real code path, which a source-level grep alone could not (an
    indirect call through a helper would slip past a grep)."""
    from app import llm as llm_module

    def _explode(*args, **kwargs):
        raise AssertionError("app.policy must never call an LLM (LAW2-01)")

    monkeypatch.setattr(llm_module, "generate", _explode)

    approved = _evaluate()
    denied = _evaluate(alert=_alert(burn_rate=None))

    assert approved.approved
    assert not denied.approved


def test_policy_module_does_not_import_llm():
    """Structural companion to the runtime test above: the module's own import
    graph has no LLM client in it at all.

    Parses the real import statements via AST rather than grepping the source -
    a substring search matches prose in docstrings (this module's own docstring
    names `from app import llm` while explaining why it is absent) and would
    also miss an aliased or conditional import that AST catches."""
    import ast

    import app.policy

    tree = ast.parse(open(app.policy.__file__, encoding="utf-8").read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(f"{module}.{alias.name}" for alias in node.names)

    assert "app.llm" not in imported
    assert not any(name.endswith(".llm") or name == "llm" for name in imported)


# --- The six checks, each failing independently ---


def test_all_checks_passing_yields_approved():
    decision = _evaluate()
    assert decision.approved
    assert decision.verdict == "approved"
    assert decision.failed_checks == []
    assert len(decision.checks) == 6
    assert decision.recommendation is None


def test_missing_burn_rate_fails_closed():
    """An alert whose burn rate cannot be read must never authorize an action."""
    decision = _evaluate(alert=_alert(burn_rate=None))
    assert not decision.approved
    assert "slo_breach" in decision.failed_checks
    assert decision.slo_value == 0.0


def test_unparseable_burn_rate_fails_closed():
    decision = _evaluate(alert=_alert(burn_rate="not-a-number"))
    assert not decision.approved
    assert "slo_breach" in decision.failed_checks


def test_burn_rate_below_threshold_is_denied():
    decision = _evaluate(alert=_alert(burn_rate="0.5"))
    assert not decision.approved
    assert "slo_breach" in decision.failed_checks


def test_low_confidence_is_denied():
    decision = _evaluate(claims=[_claim(confidence=0.4)])
    assert not decision.approved
    assert "confidence" in decision.failed_checks


def test_service_outside_sandbox_is_denied():
    decision = _evaluate(alert=_alert(service="some-other-service"))
    assert not decision.approved
    assert "sandbox_scope" in decision.failed_checks


def test_cooldown_blocks_a_second_action():
    first = _evaluate()
    assert first.approved

    policy_module.record_action_executed(SANDBOX_SERVICE)

    second = _evaluate()
    assert not second.approved
    assert "cooldown" in second.failed_checks


def test_cooldown_expires_after_the_configured_window():
    policy_module.record_action_executed(SANDBOX_SERVICE, now=0.0)
    decision = _evaluate()  # real monotonic clock is far past 0.0 + 600s
    assert "cooldown" not in decision.failed_checks


def test_unevidenced_claim_cannot_authorize_an_action():
    """LAW1-02's rule extends to actions: a claim with no evidence must not be
    able to justify a mutation any more than it can be published."""
    bare = Claim(claim="prompt_regression did it", confidence=0.99, evidence=[])
    decision = _evaluate(claims=[bare])
    assert not decision.approved
    assert "confidence" in decision.failed_checks
    assert decision.confidence == 0.0


# --- LAW2-07: the 2-approved / 2-denied split across the four seeded incidents ---


@pytest.mark.parametrize(
    "incident_type,expected_approved",
    [
        ("prompt_regression", True),
        ("retry_storm", True),
        ("retrieval_latency", False),
        ("db_pool_exhaustion", False),
    ],
)
def test_four_seeded_incidents_split_two_and_two(incident_type, expected_approved):
    """LAW2-07 verbatim. Every other check is held passing, so the split is
    produced solely by the deployment-relatedness check reading
    app.flags.DEPLOYMENT_CLASS_FLAGS - the same set Phase 3's FLAG-06 marker
    emitter uses."""
    policy_module.clear_cooldowns()
    decision = _evaluate(claims=[_claim(text=f"{incident_type} is the root cause", confidence=0.9)])
    assert decision.approved is expected_approved
    assert decision.incident_type == incident_type
    if not expected_approved:
        assert "deployment_related" in decision.failed_checks


def test_exactly_two_of_four_incidents_are_approved():
    """The aggregate form of LAW2-07 - counted, not assumed from the cases above."""
    approvals = 0
    for incident_type in ("prompt_regression", "retry_storm", "retrieval_latency", "db_pool_exhaustion"):
        policy_module.clear_cooldowns()
        decision = _evaluate(claims=[_claim(text=f"{incident_type} is the root cause")])
        approvals += int(decision.approved)
    assert approvals == 2


def test_unknown_incident_type_is_denied():
    decision = _evaluate(claims=[_claim(text="something entirely unfamiliar happened")])
    assert not decision.approved
    assert decision.incident_type is None
    assert "deployment_related" in decision.failed_checks


# --- LAW2-05: a denial hands a human something actionable ---


def test_denied_decision_carries_recommendation_and_evidence_links():
    decision = _evaluate(alert=_alert(service="some-other-service"))
    assert not decision.approved
    assert decision.recommendation is not None
    assert "did NOT execute" in decision.recommendation
    assert "sandbox_scope" in decision.recommendation
    assert decision.evidence_links == ["http://localhost:8080/trace/abc"]


# --- LAW2-06: the decision span ---


def _find_policy_span(exporter):
    spans = [s for s in exporter.get_finished_spans() if s.name == "agentk.policy.decision"]
    assert len(spans) == 1, f"expected exactly one policy span, got {len(spans)}"
    return spans[0]


def test_approved_decision_records_every_required_attribute(in_memory_exporter):
    _evaluate()
    span = _find_policy_span(in_memory_exporter)
    attrs = span.attributes
    assert attrs[AGENTK_POLICY_ACTION] == "rollback"
    assert attrs[AGENTK_POLICY_INCIDENT_ID] == "inv-1"
    assert attrs[AGENTK_POLICY_VERDICT] == "approved"
    assert attrs[AGENTK_POLICY_SLO_VALUE] == pytest.approx(2.5)
    assert attrs[AGENTK_POLICY_CONFIDENCE] == pytest.approx(0.9)
    assert attrs[AGENTK_POLICY_FAILED_CHECKS] == ""
    assert attrs[AGENTK_POLICY_REASON]


def test_denied_decision_is_recorded_as_thoroughly_as_an_approval(in_memory_exporter):
    """DASH-04 needs denied verdicts to be as queryable as approved ones, so the
    denial path must stamp the same attribute set - not a reduced one."""
    _evaluate(alert=_alert(burn_rate="0.1", service="wrong-service"))
    span = _find_policy_span(in_memory_exporter)
    attrs = span.attributes
    assert attrs[AGENTK_POLICY_VERDICT] == "denied"
    failed = attrs[AGENTK_POLICY_FAILED_CHECKS].split(",")
    assert "slo_breach" in failed
    assert "sandbox_scope" in failed
    for key in (AGENTK_POLICY_ACTION, AGENTK_POLICY_INCIDENT_ID, AGENTK_POLICY_CONFIDENCE):
        assert key in attrs
