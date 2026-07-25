"""Tests for app.telemetry's provider wiring, focused on the OTLP-export
suppression that keeps pytest's own spans out of the live SigNoz backend.
"""

from __future__ import annotations

import os

from opentelemetry import trace

from app import telemetry



# --- OTLP export suppression (test-noise containment) ---


def test_otlp_export_is_suppressed_under_pytest():
    """conftest sets the suppression flag before app.main can be imported.

    Regression guard for a real incident: pytest's spans were reaching the live
    SigNoz, and Agent K investigated them as evidence. If this assertion ever
    fails, the test suite is polluting the backend the agent reads from.
    """
    assert os.environ.get(telemetry.DISABLE_OTLP_EXPORT_ENV) in ("1", "true", "yes")


def test_providers_are_still_built_when_export_is_suppressed(monkeypatch):
    """Suppression must remove only the OTLP exporters, never the providers -
    otherwise tests would stop exercising the same instrumentation code paths
    production uses."""
    monkeypatch.setenv(telemetry.DISABLE_OTLP_EXPORT_ENV, "1")
    telemetry.setup_telemetry()
    assert trace.get_tracer_provider() is not None
    assert trace.get_tracer(__name__) is not None
