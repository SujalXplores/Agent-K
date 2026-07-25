"""Tests for the failure-injection flag store, admin token gate, deployment-marker
asymmetry (FLAG-01/FLAG-06), and the /admin/flags endpoints.

Span assertions use the in_memory_exporter fixture; the reset_flags autouse
fixture (conftest.py) guarantees each test starts from all-OFF.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import flags

# --- flag store (FLAG-01) ---


def test_get_all_defaults_all_false():
    state = flags.get_all()
    assert set(state) == set(flags.FLAG_NAMES)
    assert all(v is False for v in state.values())


def test_set_flag_round_trip_no_restart():
    assert flags.is_enabled("prompt_regression") is False
    flags.set_flag("prompt_regression", True)
    assert flags.is_enabled("prompt_regression") is True
    flags.set_flag("prompt_regression", False)
    assert flags.is_enabled("prompt_regression") is False


def test_set_flag_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        flags.set_flag("bogus", True)


def test_is_enabled_unknown_is_false():
    assert flags.is_enabled("bogus") is False


# --- admin token gate (constant-time, open-when-unset) ---


def test_token_open_when_env_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert flags.token_matches(None) is True
    assert flags.token_matches("anything") is True


def test_token_open_when_env_empty(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "")
    assert flags.token_matches(None) is True
    assert flags.token_matches("anything") is True


def test_token_enforced_when_env_set(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    assert flags.token_matches("secret") is True
    assert flags.token_matches("wrong") is False
    assert flags.token_matches(None) is False


# --- deployment-marker asymmetry (FLAG-06) ---


def _marker_spans(exporter):
    return [s for s in exporter.get_finished_spans() if s.name == "deployment.marker"]


def test_deployment_marker_emitted_for_deployment_class_on(in_memory_exporter):
    flags.maybe_emit_deployment_marker("prompt_regression", True)
    flags.maybe_emit_deployment_marker("retry_storm", True)
    spans = _marker_spans(in_memory_exporter)
    assert len(spans) == 2
    scenarios = {s.attributes["deployment.scenario"] for s in spans}
    assert scenarios == {"prompt_regression", "retry_storm"}
    assert all(
        s.attributes["deployment.version"] == f"flag-toggle-{s.attributes['deployment.scenario']}"
        for s in spans
    )


def test_no_marker_for_non_deployment_scenarios(in_memory_exporter):
    flags.maybe_emit_deployment_marker("retrieval_latency", True)
    flags.maybe_emit_deployment_marker("db_pool_exhaustion", True)
    assert _marker_spans(in_memory_exporter) == []


def test_no_marker_on_toggle_off(in_memory_exporter):
    flags.maybe_emit_deployment_marker("prompt_regression", False)
    flags.maybe_emit_deployment_marker("retry_storm", False)
    assert _marker_spans(in_memory_exporter) == []


# --- /admin/flags endpoints (FLAG-01) ---


@pytest.fixture
def app_client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_post_toggle_round_trips_via_get(app_client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = app_client.post("/admin/flags", json={"name": "retry_storm", "enabled": True})
    assert resp.status_code == 200
    assert resp.json()["flags"]["retry_storm"] is True

    getresp = app_client.get("/admin/flags")
    assert getresp.status_code == 200
    assert getresp.json()["flags"]["retry_storm"] is True


def test_post_unknown_flag_returns_422(app_client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = app_client.post("/admin/flags", json={"name": "bogus", "enabled": True})
    assert resp.status_code == 422


def test_post_wrong_token_returns_401(app_client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    resp = app_client.post(
        "/admin/flags",
        json={"name": "retry_storm", "enabled": True},
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 401
    # nothing toggled
    assert flags.is_enabled("retry_storm") is False


def test_post_correct_token_ok(app_client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    resp = app_client.post(
        "/admin/flags",
        json={"name": "retrieval_latency", "enabled": True},
        headers={"X-Admin-Token": "secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["flags"]["retrieval_latency"] is True


# --- Boot-time flag seeding (HV-3's v2-broken image) ---


def test_no_flags_seeded_by_default():
    """The all-OFF default must survive: a service never boots degraded by accident."""
    assert flags.seed_flags_from_env("") == []
    assert not any(flags.get_all().values())


def test_named_flags_are_seeded_on():
    assert flags.seed_flags_from_env("prompt_regression") == ["prompt_regression"]
    assert flags.get_all()["prompt_regression"] is True


def test_multiple_flags_seeded_with_whitespace_tolerance():
    seeded = flags.seed_flags_from_env(" prompt_regression , retry_storm ")
    assert sorted(seeded) == ["prompt_regression", "retry_storm"]


def test_unknown_seed_name_is_ignored_not_fatal():
    """A typo in a compose file must degrade to 'boots healthy', never 'refuses to boot'."""
    assert flags.seed_flags_from_env("prompt_regresion") == []
    assert not any(flags.get_all().values())
