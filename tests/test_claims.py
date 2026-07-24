"""Tests for app.claims: Evidence/Claim schema, unevidenced-claim stripping,
confidence recalibration, and evidence-link construction (LAW1-01/02/03).
"""

from __future__ import annotations

import pytest

from app.claims import (
    Claim,
    Evidence,
    build_evidence_link,
    recalibrate_confidence,
    strip_unevidenced_claims,
)


def _evidence(n: int = 1) -> list[Evidence]:
    return [
        Evidence(type="trace", query=f"q{i}", time_range="t/t", link=f"http://x/{i}")
        for i in range(n)
    ]


# --- strip_unevidenced_claims (LAW1-02) ---


def test_strip_removes_empty_evidence_claims():
    with_evidence = Claim(claim="root cause A", confidence=0.8, evidence=_evidence(1))
    without_evidence = Claim(claim="unsupported guess", confidence=0.9, evidence=[])

    result = strip_unevidenced_claims([with_evidence, without_evidence])

    assert result == [with_evidence]


def test_strip_keeps_all_when_all_have_evidence():
    claims = [Claim(claim=f"c{i}", confidence=0.5, evidence=_evidence(1)) for i in range(3)]
    assert strip_unevidenced_claims(claims) == claims


def test_strip_empty_list_returns_empty():
    assert strip_unevidenced_claims([]) == []


# --- recalibrate_confidence (LAW1-03) ---


def test_recalibrate_no_boosts_returns_llm_value_unchanged():
    assert recalibrate_confidence(0.5, evidence=[]) == 0.5


def test_recalibrate_deployment_marker_boosts():
    base = recalibrate_confidence(0.5, evidence=[])
    boosted = recalibrate_confidence(0.5, evidence=[], deployment_marker_present=True)
    assert boosted > base
    assert boosted == pytest.approx(0.65)


def test_recalibrate_more_evidence_increases_confidence():
    one = recalibrate_confidence(0.5, evidence=_evidence(1))
    three = recalibrate_confidence(0.5, evidence=_evidence(3))
    assert three > one


def test_recalibrate_evidence_boost_caps_out():
    at_cap = recalibrate_confidence(0.5, evidence=_evidence(4))
    beyond_cap = recalibrate_confidence(0.5, evidence=_evidence(10))
    assert at_cap == beyond_cap


def test_recalibrate_error_rate_delta_scales_boost():
    none = recalibrate_confidence(0.5, evidence=[], error_rate_delta=None)
    small = recalibrate_confidence(0.5, evidence=[], error_rate_delta=0.2)
    large = recalibrate_confidence(0.5, evidence=[], error_rate_delta=1.0)
    assert none < small < large


def test_recalibrate_clamps_to_zero_one():
    assert recalibrate_confidence(0.99, evidence=_evidence(10), deployment_marker_present=True) == 1.0
    assert recalibrate_confidence(0.0, evidence=[]) == 0.0


# --- build_evidence_link ---


def test_build_evidence_link_trace(monkeypatch):
    monkeypatch.setenv("SIGNOZ_URL", "http://signoz.local")
    assert build_evidence_link("trace", "abc123", "t1/t2") == "http://signoz.local/trace/abc123"


def test_build_evidence_link_log(monkeypatch):
    monkeypatch.setenv("SIGNOZ_URL", "http://signoz.local")
    link = build_evidence_link("log", "rag-service", "t1/t2")
    assert link.startswith("http://signoz.local/logs/logs-explorer?")
    assert "rag-service" in link


def test_build_evidence_link_metric(monkeypatch):
    monkeypatch.setenv("SIGNOZ_URL", "http://signoz.local")
    link = build_evidence_link("metric", "rag-service", "t1/t2")
    assert link.startswith("http://signoz.local/metrics-explorer?")


def test_build_evidence_link_deployment(monkeypatch):
    monkeypatch.setenv("SIGNOZ_URL", "http://signoz.local")
    assert build_evidence_link("deployment", "v2", "t1/t2") == "http://signoz.local/deployments?version=v2"


def test_build_evidence_link_unknown_type_raises(monkeypatch):
    monkeypatch.setenv("SIGNOZ_URL", "http://signoz.local")
    with pytest.raises(ValueError, match="unknown evidence type"):
        build_evidence_link("bogus", "x", "t1/t2")


def test_build_evidence_link_default_signoz_url(monkeypatch):
    """The unset-SIGNOZ_URL default must be the port SigNoz actually serves on.

    Pinned deliberately: this was 3301 and produced dead links on every claim
    until 2026-07-25, which is precisely the failure LAW1-05 forbids.
    """
    monkeypatch.delenv("SIGNOZ_URL", raising=False)
    assert build_evidence_link("trace", "abc", "t1/t2") == "http://localhost:8080/trace/abc"
