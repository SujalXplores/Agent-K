"""Deployment marker store (stub).

Records version changes as deployment markers. This is the in-app stub
that maps to SigNoz deployment markers when SigNoz is set up later.

Per ARCHITECTURE.md Anti-Pattern 2: marker creation is decoupled from
flag toggles. Markers are created via ``/admin/deploy`` — toggling a
failure flag does NOT auto-create a marker. This preserves the
distinction Agent K's policy gate depends on:
- Incidents 1 & 2 (prompt_regression, retry_storm) are deployment-caused
  → a marker should be created before toggling the flag
- Incidents 3 & 4 (retrieval_latency, pool_exhaustion) are NOT
  deployment-caused → no marker should be created
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.otel import get_tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/deploy", tags=["admin"])

# ─── In-memory marker store ───────────────────────────────────────────

_markers: list[dict] = []


class DeployRequest(BaseModel):
    version: str
    note: str = ""


@router.post("")
async def create_deployment(body: DeployRequest) -> dict:
    """Record a deployment marker.

    This emits a span with ``deployment.version`` so the deployment event
    is visible in telemetry. When SigNoz is connected, this maps to a
    SigNoz deployment marker.
    """
    tracer = get_tracer()
    settings = get_settings()

    timestamp = datetime.now(timezone.utc).isoformat()

    with tracer.start_as_current_span("deployment.marker") as span:
        span.set_attribute("deployment.version", body.version)
        span.set_attribute("deployment.previous_version", settings.app_version)
        span.set_attribute("deployment.timestamp", timestamp)
        span.set_attribute("deployment.note", body.note)

        marker = {
            "version": body.version,
            "previous_version": settings.app_version,
            "timestamp": timestamp,
            "note": body.note,
        }
        _markers.append(marker)

        # Update the app version in settings (so subsequent requests report
        # the new version in telemetry)
        settings.app_version = body.version

        logger.info(
            "Deployment marker created: %s → %s (%s)",
            marker["previous_version"],
            body.version,
            body.note,
        )

    return marker


@router.get("")
async def list_deployments() -> dict:
    """List all recorded deployment markers."""
    return {"markers": _markers, "current_version": get_settings().app_version}


@router.delete("")
async def clear_deployments() -> dict:
    """Clear all deployment markers (used in tests / demo reset)."""
    global _markers
    count = len(_markers)
    _markers = []
    return {"status": "cleared", "count": count}
