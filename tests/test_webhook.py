"""Tests for the inbound SigNoz alert webhook receiver (DASH-05, code half).

Covers: valid Alertmanager-shaped payload -> 200 + persisted; malformed body ->
422 + nothing persisted; secret-bearing annotation value never appears in logs;
and reachability through app.main.app (proving the router registered before
FastAPIInstrumentor.instrument_app so it is span-wrapped).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import alerts_webhook


@pytest.fixture(autouse=True)
def _clear_store():
    alerts_webhook.clear_alerts()
    yield
    alerts_webhook.clear_alerts()


def _valid_payload(secret: str = "s3cr3t-context"):
    return {
        "receiver": "agent-k",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighErrorRate", "service": "rag"},
                "annotations": {"summary": secret},
                "startsAt": "2026-07-24T10:00:00Z",
                "fingerprint": "abc123",
            }
        ],
        "groupLabels": {"alertname": "HighErrorRate"},
        "commonLabels": {"service": "rag"},
        "externalURL": "http://signoz.local",
        "version": "4",
        "groupKey": "{}:{alertname=HighErrorRate}",
    }


@pytest.fixture
def router_client():
    """A minimal app that only includes the router - isolates the receiver."""
    app = FastAPI()
    app.include_router(alerts_webhook.router)
    with TestClient(app) as c:
        yield c


def test_valid_payload_persists_and_returns_count(router_client):
    resp = router_client.post("/alerts/webhook", json=_valid_payload())
    assert resp.status_code == 200
    assert resp.json() == {"received": 1}

    persisted = alerts_webhook.get_alerts()
    assert len(persisted) == 1
    rec = persisted[0]
    assert rec["alertname"] == "HighErrorRate"
    assert rec["status"] == "firing"
    assert rec["startsAt"] == "2026-07-24T10:00:00Z"
    assert rec["fingerprint"] == "abc123"
    assert rec["labels"]["service"] == "rag"


def test_malformed_payload_returns_422_and_persists_nothing(router_client):
    # AlertItem missing required startsAt
    bad = _valid_payload()
    del bad["alerts"][0]["startsAt"]
    resp = router_client.post("/alerts/webhook", json=bad)
    assert resp.status_code == 422
    assert alerts_webhook.get_alerts() == []


def test_missing_top_level_field_returns_422(router_client):
    bad = _valid_payload()
    del bad["receiver"]
    resp = router_client.post("/alerts/webhook", json=bad)
    assert resp.status_code == 422
    assert alerts_webhook.get_alerts() == []


def test_secret_annotation_not_logged(router_client, caplog):
    with caplog.at_level("INFO"):
        resp = router_client.post("/alerts/webhook", json=_valid_payload("TOP-SECRET-VALUE"))
    assert resp.status_code == 200
    # the annotation value is persisted for Phase 5 but never dumped to logs
    assert any(r["annotations"]["summary"] == "TOP-SECRET-VALUE" for r in alerts_webhook.get_alerts())
    assert all("TOP-SECRET-VALUE" not in rec.message for rec in caplog.records)


def test_reachable_via_main_app():
    """The route resolves and returns 200 through the fully-instrumented app.main.app."""
    from app.main import app as main_app

    with TestClient(main_app) as c:
        resp = c.post("/alerts/webhook", json=_valid_payload())
    assert resp.status_code == 200
    assert resp.json() == {"received": 1}
