"""Tests for app.rollback: Agent K's act stage and its independent recovery
verification (LAW2-03/04).

Both the deployer sidecar and the SigNoz MCP wrapper are monkeypatched - these
tests are about what Agent K does with the answers, not about either dependency.
The recurring theme is fail-closed verification: every way of NOT being able to
prove recovery must produce verified=False, never an optimistic True.
"""

from __future__ import annotations

import pytest
from mcp.types import CallToolResult, TextContent

from app import policy as policy_module
from app import rollback as rollback_module
from app import signoz_mcp
from app.observability import (
    AGENTK_ACTION_KIND,
    AGENTK_ACTION_PREVIOUS_IMAGE,
    AGENTK_ACTION_STATUS,
    AGENTK_ACTION_VERIFIED,
)
from app.policy import PolicyCheck, PolicyDecision

SANDBOX_SERVICE = "agent-k-rag-service"
TIME_RANGE = "2026-07-25T10:00:00Z/now"


@pytest.fixture(autouse=True)
def _clear_cooldowns():
    policy_module.clear_cooldowns()
    yield
    policy_module.clear_cooldowns()


async def _no_sleep(_seconds: float) -> None:
    """Skip the real 30s verification wait."""
    return None


def _decision(verdict: str = "approved") -> PolicyDecision:
    return PolicyDecision(
        action="rollback",
        incident_id="inv-42",
        verdict=verdict,
        reason="test",
        checks=[PolicyCheck("slo_breach", verdict == "approved", "test")],
        target_service=SANDBOX_SERVICE,
        confidence=0.9,
    )


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


def _mock_deployer(monkeypatch, response: _FakeResponse):
    calls: list[bool] = []

    async def _fake():
        calls.append(True)
        return response

    monkeypatch.setattr(rollback_module, "_call_deployer", _fake)
    return calls


def _mock_verification(monkeypatch, text: str, is_error: bool = False):
    async def _fake(tool_name, arguments):
        return CallToolResult(content=[TextContent(type="text", text=text)], isError=is_error)

    monkeypatch.setattr(signoz_mcp, "query_signoz", _fake)


_SUCCESS_BODY = {
    "status": "rolled_back",
    "service": "rag-app",
    "previous_image": "agent-k-rag:v2-broken",
    "rolled_back_to": "v1-good",
}


# --- The gate cannot be bypassed ---


@pytest.mark.asyncio
async def test_denied_decision_is_never_executed(monkeypatch):
    """A second, redundant check on top of the caller's. This is the difference
    between 'we remember to call the gate' and 'the gate cannot be bypassed'."""
    calls = _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))

    outcome = await rollback_module.execute_rollback(
        decision=_decision("denied"), time_range=TIME_RANGE, sleep=_no_sleep
    )

    assert outcome.status == "skipped"
    assert not outcome.executed
    assert calls == [], "no HTTP call may be made for a denied decision"


@pytest.mark.asyncio
async def test_denied_decision_does_not_start_a_cooldown(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    await rollback_module.execute_rollback(
        decision=_decision("denied"), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert policy_module.seconds_since_last_action(SANDBOX_SERVICE) is None


# --- The happy path ---


@pytest.mark.asyncio
async def test_approved_rollback_executes_and_verifies(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "error_rate: 0.01")

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )

    assert outcome.status == "executed"
    assert outcome.previous_image == "agent-k-rag:v2-broken"
    assert outcome.rolled_back_to == "v1-good"
    assert outcome.verified is True


@pytest.mark.asyncio
async def test_execution_starts_the_cooldown(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "error_rate: 0.01")

    await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )

    elapsed = policy_module.seconds_since_last_action(SANDBOX_SERVICE)
    assert elapsed is not None and elapsed >= 0


# --- Sidecar-reported failures ---


@pytest.mark.asyncio
async def test_conflict_is_reported_as_conflict(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(409))
    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.status == "conflict"
    assert outcome.verified is False


@pytest.mark.asyncio
async def test_server_error_is_reported_as_failed(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(500))
    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.status == "failed"
    assert outcome.verified is False


@pytest.mark.asyncio
async def test_failed_call_does_not_start_a_cooldown(monkeypatch):
    """A failure must be retryable rather than blocked by a cooldown that never
    protected anything."""
    _mock_deployer(monkeypatch, _FakeResponse(500))
    await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert policy_module.seconds_since_last_action(SANDBOX_SERVICE) is None


@pytest.mark.asyncio
async def test_transport_exception_is_caught(monkeypatch):
    async def _explode():
        raise ConnectionError("deployer unreachable")

    monkeypatch.setattr(rollback_module, "_call_deployer", _explode)

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.status == "failed"
    assert "exception" in outcome.verification_detail


# --- LAW2-04: verification fails closed ---


@pytest.mark.asyncio
async def test_unparseable_evidence_is_not_verified(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "some entirely unrelated payload")

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.status == "executed"
    assert outcome.verified is False
    assert "could not parse" in outcome.verification_detail


@pytest.mark.asyncio
async def test_still_elevated_error_rate_is_not_verified(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "error_rate: 0.42")

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.verified is False
    assert "still above" in outcome.verification_detail


@pytest.mark.asyncio
async def test_verification_query_error_is_not_verified(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "irrelevant", is_error=True)

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.verified is False


@pytest.mark.asyncio
async def test_verification_exception_is_not_verified(monkeypatch):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))

    async def _explode(tool_name, arguments):
        raise RuntimeError("MCP down")

    monkeypatch.setattr(signoz_mcp, "query_signoz", _explode)

    outcome = await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )
    assert outcome.status == "executed", "the rollback itself did happen"
    assert outcome.verified is False, "but recovery was never proven"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("error_rate: 0.01", 0.01),
        ("error rate = 0.5", 0.5),
        ("ERROR_RATE 1", 1.0),
        ("no numbers here", None),
    ],
)
def test_error_rate_parsing(text, expected):
    assert rollback_module._parse_error_rate(text) == expected


# --- Telemetry ---


@pytest.mark.asyncio
async def test_action_span_records_outcome(monkeypatch, in_memory_exporter):
    _mock_deployer(monkeypatch, _FakeResponse(200, _SUCCESS_BODY))
    _mock_verification(monkeypatch, "error_rate: 0.01")

    await rollback_module.execute_rollback(
        decision=_decision(), time_range=TIME_RANGE, sleep=_no_sleep
    )

    spans = [
        s for s in in_memory_exporter.get_finished_spans() if s.name == "agentk.action.rollback"
    ]
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs[AGENTK_ACTION_KIND] == "rollback"
    assert attrs[AGENTK_ACTION_STATUS] == "executed"
    assert attrs[AGENTK_ACTION_VERIFIED] is True
    assert attrs[AGENTK_ACTION_PREVIOUS_IMAGE] == "agent-k-rag:v2-broken"
