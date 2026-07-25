"""Tests for app.investigation: the state machine, evidence gathering, hypothesis
formation, loop breaker, cost watchdog, span links, and Law 3 self-telemetry
(INV-01/02/03, LAW1-04, LAW3-01..06).

app.signoz_mcp.query_signoz and app.llm.generate are monkeypatched throughout - no
real SigNoz MCP server, live stack, or LLM provider credential is required.
"""

from __future__ import annotations

import json
import time

import pytest
from mcp.types import CallToolResult, TextContent

from app import investigation as inv_module
from app import llm as llm_module
from app import signoz_mcp
from app.alerts_webhook import AlertItem
from app.llm import LlmResult
from app.observability import AGENTK_INVESTIGATION_STATE, AGENTK_WATCHDOG_KIND


@pytest.fixture(autouse=True)
def _clear_investigations():
    inv_module.clear_investigations()
    yield
    inv_module.clear_investigations()


def _alert(labels=None, annotations=None) -> AlertItem:
    return AlertItem(
        status="firing",
        labels={"alertname": "TestAlert", "service": "rag-service", **(labels or {})},
        annotations=annotations or {},
        startsAt="2026-07-24T10:00:00Z",
        fingerprint="abc123",
    )


def _mock_query_success(text: str = "evidence text"):
    async def _fake(tool_name, arguments):
        return CallToolResult(content=[TextContent(type="text", text=text)], isError=False)

    return _fake


def _mock_generate(claim: str, confidence: float, input_tokens: int = 10, output_tokens: int = 10):
    def _fake(prompt, system=None):
        return LlmResult(
            answer=json.dumps({"claim": claim, "confidence": confidence}),
            model="test-model",
            provider="test-provider",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return _fake


# --- _record_mcp_query_and_check_loop ---


def test_loop_counter_returns_none_until_threshold_exceeded():
    inv = inv_module.Investigation(id="i1", alert=_alert())
    for _ in range(inv_module.LOOP_BREAKER_REPEAT_THRESHOLD):
        assert inv_module._record_mcp_query_and_check_loop(inv, "t", {"a": 1}) is None
    triggered = inv_module._record_mcp_query_and_check_loop(inv, "t", {"a": 1})
    assert triggered is not None


# --- _parse_hypothesis_response ---


def test_parse_valid_json():
    conf, claim = inv_module._parse_hypothesis_response('{"claim": "x broke", "confidence": 0.9}')
    assert claim == "x broke"
    assert conf == 0.9


def test_parse_malformed_json_falls_back():
    conf, claim = inv_module._parse_hypothesis_response("not json at all")
    assert conf == 0.1
    assert "unparsed model response" in claim


def test_parse_out_of_range_confidence_clamped():
    conf, _ = inv_module._parse_hypothesis_response('{"claim": "x", "confidence": 5.0}')
    assert conf == 1.0


# --- span links (LAW1-04) ---


def test_span_context_extracted_when_present():
    alert = _alert(labels={"trace_id": "1" * 32, "span_id": "2" * 16})
    ctx = inv_module._extract_incident_span_context(alert)
    assert ctx is not None
    assert len(inv_module._build_incident_links(alert)) == 1


def test_span_context_none_when_absent():
    alert = _alert()
    assert inv_module._extract_incident_span_context(alert) is None
    assert inv_module._build_incident_links(alert) == []


def test_span_context_none_when_malformed_hex():
    alert = _alert(labels={"trace_id": "not-hex", "span_id": "2" * 16})
    assert inv_module._extract_incident_span_context(alert) is None


# --- run_investigation: happy path ---


@pytest.mark.asyncio
async def test_run_investigation_reaches_reported_with_evidence_backed_claim(
    monkeypatch, in_memory_exporter
):
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success("deployment marker present"))
    monkeypatch.setattr(llm_module, "generate", _mock_generate("prompt_regression suspected", 0.9))

    inv = await inv_module.run_investigation(_alert())

    assert inv.state == inv_module.InvestigationState.REPORTED
    assert inv.incomplete is False
    assert len(inv.claims) >= 1
    assert all(c.evidence for c in inv.claims)  # LAW1-02 already enforced

    spans = [s for s in in_memory_exporter.get_finished_spans() if s.name == "agentk.investigation"]
    assert len(spans) == 1
    assert spans[0].attributes[AGENTK_INVESTIGATION_STATE] == "reported"

    assert inv_module.get_investigation(inv.id) is inv


@pytest.mark.asyncio
async def test_run_investigation_stops_early_on_high_confidence(monkeypatch):
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(llm_module, "generate", _mock_generate("root cause found", 0.95))

    inv = await inv_module.run_investigation(_alert())

    # Stops as soon as it is allowed to, but NOT before MIN_EVIDENCE_ITERATIONS.
    # A 0.95-confidence answer drawn from one query is not a finished
    # investigation - it has not yet looked at the deployment marker that decides
    # the deployment_related policy check.
    assert inv.mcp_query_count == inv_module.MIN_EVIDENCE_ITERATIONS
    assert inv.mcp_query_count < inv_module.MAX_ITERATIONS


# --- loop breaker (LAW3-04/06) ---


@pytest.mark.asyncio
async def test_loop_breaker_fires_on_adversarial_repeated_query(monkeypatch, in_memory_exporter):
    # Force every iteration to issue the IDENTICAL query (adversarial/buggy case) -
    # normal operation varies the query per iteration (see module docstring), so
    # this must be deliberately forced to prove the breaker actually fires.
    monkeypatch.setattr(
        inv_module,
        "EVIDENCE_QUERY_PLAN",
        [(inv_module.SIGNOZ_TRACES_TOOL, "trace", inv_module._error_spans_args)] * 10,
    )
    monkeypatch.setattr(inv_module, "MAX_ITERATIONS", 10)
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(llm_module, "generate", _mock_generate("low confidence guess", 0.1))

    inv = await inv_module.run_investigation(_alert())

    assert inv.loop_breaker_fired is True
    assert inv.state == inv_module.InvestigationState.ESCALATED
    assert inv.incomplete is True
    assert any(e["kind"] == "loop_breaker" for e in inv.watchdog_events)
    assert inv.mcp_query_count <= inv_module.LOOP_BREAKER_REPEAT_THRESHOLD + 1  # stopped well short of 10

    spans = [
        s for s in in_memory_exporter.get_finished_spans() if s.name == "agentk.watchdog.loop_breaker"
    ]
    assert len(spans) == 1
    assert spans[0].attributes[AGENTK_WATCHDOG_KIND] == "loop_breaker"


# --- cost watchdog (LAW3-05) ---


@pytest.mark.asyncio
async def test_cost_watchdog_fires_on_forced_budget_overrun(monkeypatch, in_memory_exporter):
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(
        llm_module,
        "generate",
        _mock_generate(
            "low confidence guess", 0.1, input_tokens=inv_module.TOKEN_BUDGET, output_tokens=1
        ),
    )

    inv = await inv_module.run_investigation(_alert())

    assert inv.cost_watchdog_fired is True
    assert inv.state == inv_module.InvestigationState.ESCALATED
    assert inv.incomplete is True
    assert any(e["kind"] == "cost_budget" for e in inv.watchdog_events)

    spans = [s for s in in_memory_exporter.get_finished_spans() if s.name == "agentk.watchdog.cost_budget"]
    assert len(spans) == 1


# --- unexpected exception still reaches a terminal state ---


@pytest.mark.asyncio
async def test_unexpected_exception_still_reaches_terminal_state(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("unexpected bug")

    monkeypatch.setattr(inv_module, "_gather_evidence", _boom)

    inv = await inv_module.run_investigation(_alert())

    assert inv.state == inv_module.InvestigationState.ESCALATED
    assert inv.incomplete is True
    assert inv_module.get_investigation(inv.id) is inv


# --- four seeded incident types (INV-03) ---


@pytest.mark.parametrize(
    "incident_type,evidence_text",
    [
        ("prompt_regression", "rag.prompt_construction.regression_active=true deployment marker present"),
        ("retry_storm", "agentk.llm.retry_count=5 cost spike, no deployment marker"),
        ("retrieval_latency", "rag.retrieval span duration 2000ms, latency_injected=true"),
        ("db_pool_exhaustion", "simulated DB pool exhaustion error in logs"),
    ],
)
@pytest.mark.asyncio
async def test_produces_hypothesis_for_each_seeded_incident_type(monkeypatch, incident_type, evidence_text):
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success(evidence_text))
    monkeypatch.setattr(
        llm_module, "generate", _mock_generate(f"{incident_type} is the likely root cause", 0.85)
    )

    inv = await inv_module.run_investigation(_alert())

    assert inv.state == inv_module.InvestigationState.REPORTED
    assert len(inv.claims) >= 1
    assert incident_type in inv.claims[0].claim


# --- start_investigation (INV-01) ---


@pytest.mark.asyncio
async def test_start_investigation_schedules_a_background_task(monkeypatch):
    called = {}

    async def _fake_run(alert):
        called["alert"] = alert
        return inv_module.Investigation(id="scheduled", alert=alert)

    monkeypatch.setattr(inv_module, "run_investigation", _fake_run)

    alert = _alert()
    task = inv_module.start_investigation(alert)
    result = await task

    assert called["alert"] is alert
    assert result.id == "scheduled"


# --- in-process store ---


def test_list_and_clear_investigations():
    inv_module._investigations["x"] = inv_module.Investigation(id="x", alert=_alert())
    assert len(inv_module.list_investigations()) == 1
    inv_module.clear_investigations()
    assert inv_module.list_investigations() == []
    assert inv_module.get_investigation("x") is None


# --- Law 2 act stage wiring (Phase 6) ---
#
# These prove the gate is actually REACHED by the state machine, not merely that
# app/policy.py works in isolation (tests/test_policy.py covers that). The
# distinction matters: a correct policy module that nothing calls enforces nothing.


def _actionable_alert():
    """An alert that clears every policy check except the incident-type one, so
    each test below turns solely on what the LLM diagnoses."""
    return _alert(
        labels={"service": "agent-k-rag-service"},
        annotations={"burn_rate": "2.5"},
    )


@pytest.mark.asyncio
async def test_deployment_class_incident_reaches_an_approved_rollback(monkeypatch):
    from app import policy as policy_module
    from app import rollback as rollback_module

    policy_module.clear_cooldowns()
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success("deployment marker present"))
    monkeypatch.setattr(llm_module, "generate", _mock_generate("prompt_regression is the cause", 0.9))

    executed = []

    async def _fake_execute(*, decision, time_range, sleep=None):
        executed.append(decision)
        return rollback_module.ActionOutcome(kind="rollback", status="executed", verified=True)

    monkeypatch.setattr(rollback_module, "execute_rollback", _fake_execute)

    inv = await inv_module.run_investigation(_actionable_alert())

    assert inv.policy_decision is not None
    assert inv.policy_decision.approved
    assert len(executed) == 1
    assert inv.action_outcome is not None and inv.action_outcome.executed


@pytest.mark.asyncio
async def test_non_deployment_incident_is_denied_and_takes_no_action(monkeypatch):
    from app import policy as policy_module
    from app import rollback as rollback_module

    policy_module.clear_cooldowns()
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(llm_module, "generate", _mock_generate("retrieval_latency is the cause", 0.9))

    async def _must_not_run(*, decision, time_range, sleep=None):
        raise AssertionError("no action may execute on a denied verdict (LAW2-05)")

    monkeypatch.setattr(rollback_module, "execute_rollback", _must_not_run)

    inv = await inv_module.run_investigation(_actionable_alert())

    assert inv.policy_decision is not None
    assert not inv.policy_decision.approved
    assert "deployment_related" in inv.policy_decision.failed_checks
    assert inv.action_outcome is None
    # LAW2-05: the human gets an evidence-linked recommendation instead.
    assert inv.policy_decision.recommendation is not None
    assert inv.policy_decision.evidence_links


@pytest.mark.asyncio
async def test_incomplete_investigation_never_reaches_the_act_stage(monkeypatch):
    """A loop-broken investigation stopped early by definition, so acting on its
    half-formed picture is exactly what Law 3's watchdogs exist to prevent."""
    from app import rollback as rollback_module

    monkeypatch.setattr(
        inv_module,
        "EVIDENCE_QUERY_PLAN",
        [(inv_module.SIGNOZ_TRACES_TOOL, "trace", inv_module._error_spans_args)] * 10,
    )
    monkeypatch.setattr(inv_module, "MAX_ITERATIONS", 10)
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    # Confidence must stay BELOW CONFIDENCE_STOP_THRESHOLD: a high-confidence
    # hypothesis stops the loop on iteration 1, so the breaker would never get
    # the repeat count it needs and this test would silently assert nothing.
    monkeypatch.setattr(llm_module, "generate", _mock_generate("prompt_regression is the cause", 0.1))

    async def _must_not_run(*, decision, time_range, sleep=None):
        raise AssertionError("an incomplete investigation must never act")

    monkeypatch.setattr(rollback_module, "execute_rollback", _must_not_run)

    inv = await inv_module.run_investigation(_actionable_alert())

    assert inv.loop_breaker_fired is True
    assert inv.incomplete is True
    # The sharp assertion: policy was never even EVALUATED. Were the incomplete
    # guard removed, this would hold a denial rather than None - so None is what
    # uniquely proves the guard fired, rather than some later check happening to
    # deny the action anyway.
    assert inv.policy_decision is None
    assert inv.action_outcome is None


@pytest.mark.asyncio
async def test_policy_decision_span_is_a_child_of_the_investigation_span(
    monkeypatch, in_memory_exporter
):
    """A human opening agentk.investigation should see the verdict in the same
    trace as the reasoning that produced it."""
    from app import policy as policy_module

    policy_module.clear_cooldowns()
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(llm_module, "generate", _mock_generate("retrieval_latency is the cause", 0.9))

    await inv_module.run_investigation(_actionable_alert())

    spans = {s.name: s for s in in_memory_exporter.get_finished_spans()}
    assert "agentk.policy.decision" in spans
    policy_span = spans["agentk.policy.decision"]
    investigation_span = spans["agentk.investigation"]
    assert policy_span.parent is not None
    assert policy_span.parent.span_id == investigation_span.context.span_id


@pytest.mark.asyncio
async def test_act_stage_failure_does_not_destroy_the_investigation_record(monkeypatch):
    """Law 1/3 telemetry must survive an act-stage crash."""
    from app import policy as policy_module

    policy_module.clear_cooldowns()
    monkeypatch.setattr(signoz_mcp, "query_signoz", _mock_query_success())
    monkeypatch.setattr(llm_module, "generate", _mock_generate("prompt_regression is the cause", 0.9))

    def _explode(**kwargs):
        raise RuntimeError("policy blew up")

    monkeypatch.setattr(policy_module, "evaluate_policy", _explode)

    inv = await inv_module.run_investigation(_actionable_alert())

    assert inv.state == inv_module.InvestigationState.REPORTED
    assert inv.claims
    assert inv_module.get_investigation(inv.id) is inv


# --- SigNoz MCP tool contract (corrected 2026-07-25 against server v0.9.0) ---


def test_evidence_plan_uses_real_signoz_mcp_tool_names():
    """Pins the tool names against signoz-mcp-server's advertised inventory.

    These were originally query_traces/query_logs/query_metrics - names that do not
    exist. A wrong name does not crash: it returns an error result, which reads
    exactly like "no evidence found", so every investigation silently escalated and
    nothing pointed at the cause. This test makes that failure loud.
    """
    names = [tool for tool, _, _ in inv_module.EVIDENCE_QUERY_PLAN]
    assert names == [
        "signoz_aggregate_traces",  # p95 latency per operation - symptom, all scenarios
        "signoz_search_traces",     # error spans - symptom, error scenarios only
        "signoz_aggregate_traces",  # deployment.marker grouped by scenario - the cause
        "signoz_search_logs",
        "signoz_aggregate_traces",
    ]
    assert all(name.startswith("signoz_") for name in names)


def test_every_evidence_query_is_distinct():
    """The loop breaker must only fire on a genuine repeat, never on the plan itself."""
    time_args = {"timeRange": "1h"}
    hashes = {
        signoz_mcp.compute_query_hash(tool, build(("svc"), time_args))
        for tool, _, build in inv_module.EVIDENCE_QUERY_PLAN
    }
    assert len(hashes) == len(inv_module.EVIDENCE_QUERY_PLAN)


def test_trace_stats_query_avoids_metric_name_requirement():
    """signoz_query_metrics requires a metricName this app never emits, so the
    error-rate signal is derived from spans instead."""
    args = inv_module._trace_stats_args("svc", {"timeRange": "1h"})
    assert args["aggregation"] == "count"
    assert args["groupBy"] == "has_error"
    assert "metricName" not in args


def test_time_args_prefer_the_alerts_own_window():
    alert = _alert()
    alert.startsAt = "2026-07-25T10:00:00Z"
    alert.endsAt = "2026-07-25T10:30:00Z"
    args = inv_module.build_time_args(alert)
    assert args == {"start": 1784973600000, "end": 1784975400000}


def test_time_args_fall_back_when_the_window_is_unusable():
    """A missing, malformed, or inverted window becomes a relative range rather
    than a nonsense absolute one."""
    for starts, ends in [("", None), ("not-a-date", None), ("2026-07-25T10:30:00Z", "2026-07-25T10:00:00Z")]:
        alert = _alert()
        alert.startsAt = starts
        alert.endsAt = ends
        assert inv_module.build_time_args(alert) == {"timeRange": inv_module.DEFAULT_TIME_RANGE}


def test_open_ended_alert_uses_now_as_the_end():
    """A still-firing alert (endsAt=None) gets a window ending at 'now'.

    The start must be genuinely in the past: a future startsAt would produce an
    inverted window and correctly take the relative-range fallback instead.
    """
    alert = _alert()
    alert.startsAt = "2026-07-20T10:00:00Z"
    alert.endsAt = None
    args = inv_module.build_time_args(alert)
    assert args["start"] == 1784541600000
    assert args["end"] > args["start"]


def test_signoz_web_url_is_preferred_over_a_hand_built_link():
    """SigNoz's own deep link cannot disagree with SigNoz's own routes."""
    text = '{"trace_id": "abc", "webUrl": "http://localhost:8080/trace/abc?x=1"}'
    assert inv_module.extract_web_url(text) == "http://localhost:8080/trace/abc?x=1"


def test_missing_web_url_falls_back_to_the_built_link():
    assert inv_module.extract_web_url('{"trace_id": "abc"}') is None


def test_time_window_is_frozen_for_the_whole_investigation():
    """Regression: the loop breaker is defeated by a moving timestamp.

    An open-ended alert's window ends at "now". If that is recomputed per query,
    the `end` millisecond changes between iterations, so two IDENTICAL queries hash
    differently and the LAW3-04 loop breaker can never fire. The bug was
    intermittent - it only surfaced when iterations straddled a millisecond
    boundary - so it is pinned here rather than left to timing.
    """
    alert = _alert()
    alert.startsAt = "2026-07-20T10:00:00Z"
    alert.endsAt = None
    inv = inv_module.Investigation(id="i1", alert=alert)

    first = dict(inv.time_args)
    time.sleep(0.005)
    second = dict(inv.time_args)
    assert first == second

    args_a = inv_module._error_spans_args("svc", inv.time_args)
    time.sleep(0.005)
    args_b = inv_module._error_spans_args("svc", inv.time_args)
    assert signoz_mcp.compute_query_hash("signoz_search_traces", args_a) == \
        signoz_mcp.compute_query_hash("signoz_search_traces", args_b)
