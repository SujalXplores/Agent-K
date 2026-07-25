"""Tests for POST /admin/reset - the one-call demo-state clearer.

Covers: the endpoint clears flags, alerts, investigations, and cooldowns in a
single call; token gate mirrors /admin/flags (open when unset, enforced when
set); and the response reports what was cleared.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import alerts_webhook, flags, investigation, policy


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Start each test from empty stores, and restore emptiness after.

    Also clears ADMIN_TOKEN so the endpoint is open by default - the .env on
    this machine has it set, and the conftest isolate_from_dotenv fixture
    neuters load_dotenv but cannot undo a value already loaded into os.environ
    before the test process started importing app modules.
    """
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    alerts_webhook.clear_alerts()
    investigation.clear_investigations()
    policy.clear_cooldowns()
    for name in flags.FLAG_NAMES:
        flags.set_flag(name, False)
    yield
    alerts_webhook.clear_alerts()
    investigation.clear_investigations()
    policy.clear_cooldowns()
    for name in flags.FLAG_NAMES:
        flags.set_flag(name, False)


@pytest.fixture
def client():
    """TestClient on the full app.main, with OTLP export suppressed (conftest)."""
    from app.main import app

    with TestClient(app) as c:
        yield c


def _seed_some_state():
    """Populate every in-process store so reset has something to clear."""
    flags.set_flag("prompt_regression", True)
    flags.set_flag("retry_storm", True)
    policy.record_action_executed("agent-k-rag-service")
    # Persist one alert so the alert store is non-empty.
    alerts_webhook._persist_alert(
        "agent-k",
        alerts_webhook.AlertItem(
            status="firing",
            labels={"alertname": "HighErrorRate"},
            annotations={},
            startsAt="2026-07-25T10:00:00Z",
        ),
    )


def test_reset_clears_all_stores(client, monkeypatch):
    # Delete ADMIN_TOKEN here (not just in the autouse fixture) because app.main
    # is imported lazily inside the client fixture, and setup_telemetry()'s
    # load_dotenv() re-loads it from .env after the autouse fixture's delenv.
    # This mirrors the pattern in tests/test_flags.py.
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    _seed_some_state()
    assert flags.is_enabled("prompt_regression") is True
    assert len(alerts_webhook.get_alerts()) == 1
    assert policy.seconds_since_last_action("agent-k-rag-service") is not None

    resp = client.post("/admin/reset")

    assert resp.status_code == 200
    body = resp.json()
    assert body["reset"] is True
    assert body["cleared"]["alerts"] == 1
    assert body["cleared"]["flags"] == "all_off"
    assert body["cleared"]["cooldowns"] == "cleared"

    # Every store is now empty / default.
    assert flags.is_enabled("prompt_regression") is False
    assert flags.is_enabled("retry_storm") is False
    assert alerts_webhook.get_alerts() == []
    assert policy.seconds_since_last_action("agent-k-rag-service") is None


def test_reset_open_when_admin_token_unset(client, monkeypatch):
    """With ADMIN_TOKEN unset, the endpoint is open (local-demo convenience)."""
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = client.post("/admin/reset")
    assert resp.status_code == 200


def test_reset_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    resp = client.post("/admin/reset", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 401


def test_reset_accepts_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    resp = client.post("/admin/reset", headers={"X-Admin-Token": "secret"})
    assert resp.status_code == 200


def test_reset_on_empty_state_reports_zero(client, monkeypatch):
    """Resetting an already-clean store is a no-op that still returns 200."""
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = client.post("/admin/reset")
    assert resp.status_code == 200
    assert resp.json()["cleared"]["alerts"] == 0
