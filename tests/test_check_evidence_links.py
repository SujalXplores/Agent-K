"""Tests for scripts/check_evidence_links.py (LAW1-05, code half).

Uses an httpx MockTransport for fully deterministic, offline link resolution -
no real network access or live SigNoz instance required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_evidence_links import check_links, collect_links_from_investigations  # noqa: E402


_REAL_CLIENT = httpx.Client


def _mock_client_factory(status_map: dict[str, int]):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        status = status_map.get(url, 599)
        return httpx.Response(status, request=request)

    return lambda **kwargs: _REAL_CLIENT(transport=httpx.MockTransport(handler))


def test_check_links_all_resolve(monkeypatch):
    urls = ["http://signoz.local/trace/abc", "http://signoz.local/trace/def"]
    monkeypatch.setattr(
        httpx, "Client", _mock_client_factory({u: 200 for u in urls})
    )

    results = check_links(urls)

    assert len(results) == 2
    assert all(r["resolved"] for r in results)
    assert all(r["status"] == 200 for r in results)


def test_check_links_some_fail(monkeypatch):
    urls = ["http://signoz.local/trace/ok", "http://signoz.local/trace/missing"]
    monkeypatch.setattr(
        httpx,
        "Client",
        _mock_client_factory({"http://signoz.local/trace/ok": 200, "http://signoz.local/trace/missing": 404}),
    )

    results = check_links(urls)

    resolved = {r["link"]: r["resolved"] for r in results}
    assert resolved["http://signoz.local/trace/ok"] is True
    assert resolved["http://signoz.local/trace/missing"] is False


def test_check_links_connection_error_counts_as_unresolved(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: _REAL_CLIENT(transport=httpx.MockTransport(handler))
    )

    results = check_links(["http://signoz.local/trace/unreachable"])

    assert results[0]["resolved"] is False
    assert results[0]["status"] is None
    assert results[0]["error"] is not None


def test_check_links_3xx_counts_as_resolved(monkeypatch):
    url = "http://signoz.local/trace/redirected"
    monkeypatch.setattr(httpx, "Client", _mock_client_factory({url: 302}))

    results = check_links([url])

    assert results[0]["resolved"] is True


def test_collect_links_from_investigations_empty_by_default():
    from app import investigation

    investigation.clear_investigations()
    assert collect_links_from_investigations() == []


def test_collect_links_from_investigations_gathers_all_claim_evidence():
    from app import investigation
    from app.alerts_webhook import AlertItem
    from app.claims import Claim, Evidence

    investigation.clear_investigations()
    alert = AlertItem(status="firing", labels={}, startsAt="2026-07-24T10:00:00Z")
    inv = investigation.Investigation(id="test-inv", alert=alert)
    inv.claims = [
        Claim(
            claim="x",
            confidence=0.8,
            evidence=[Evidence(type="trace", query="q", time_range="t/t", link="http://a/1")],
        ),
        Claim(
            claim="y",
            confidence=0.5,
            evidence=[Evidence(type="log", query="q2", time_range="t/t", link="http://a/2")],
        ),
    ]
    investigation._investigations["test-inv"] = inv

    links = collect_links_from_investigations()

    assert set(links) == {"http://a/1", "http://a/2"}
    investigation.clear_investigations()
