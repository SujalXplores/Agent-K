"""Tests for app.investigation: the state machine, evidence gathering, hypothesis
formation, loop breaker, cost watchdog, span links, and Law 3 self-telemetry
(INV-01/02/03, LAW1-04, LAW3-01..06).

app.signoz_mcp.query_signoz and app.llm.generate are monkeypatched throughout - no
real SigNoz MCP server, live stack, or LLM provider credential is required.
"""

from __future__ import annotations

import json

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

    assert inv.mcp_query_count == 1  # stopped after the first iteration


# --- loop breaker (LAW3-04/06) ---


@pytest.mark.asyncio
async def test_loop_breaker_fires_on_adversarial_repeated_query(monkeypatch, in_memory_exporter):
    # Force every iteration to issue the IDENTICAL query (adversarial/buggy case) -
    # normal operation varies the query per iteration (see module docstring), so
    # this must be deliberately forced to prove the breaker actually fires.
    monkeypatch.setattr(
        inv_module, "EVIDENCE_QUERY_PLAN", [(inv_module.SIGNOZ_TRACES_TOOL, "trace")] * 10
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
