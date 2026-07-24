"""Inbound SigNoz alert webhook receiver (DASH-05, code half).

A real, reusable `POST /alerts/webhook` entrypoint - deliberately NOT a throwaway.
It is designed to be the actual trigger Agent K's Phase-5 investigation loop
consumes (INV-01), so proving the entry path end-to-end now de-risks Phase 5.
The SigNoz-UI half of DASH-05 (building the alert rule + webhook notification
channel and confirming an end-to-end fire) is the human-action Plan 03-05.

The payload is Alertmanager-shaped (SigNoz forwards Alertmanager-format webhooks -
03-RESEARCH.md Key Finding 2). The Pydantic models here are a NARROW, strict field
set - not a generic/flexible parser - so a malformed or unexpected body is rejected
with 422 before any processing (T-03-13). Persistence is an in-process list
(sufficient for validate/log/persist; Phase 5 owns durable handling).

Content-safety (mirrors app/observability.py discipline): the log line emits only
the alert name + status. The raw labels/annotations values are persisted for Phase 5
to consume but are never dumped to logs, since they can carry sensitive incident
context (T-03-15).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class AlertItem(BaseModel):
    """A single alert within an Alertmanager-shaped webhook payload."""

    status: str
    labels: dict[str, str]
    annotations: dict[str, str] = {}
    startsAt: str
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhookPayload(BaseModel):
    """The narrow SigNoz/Alertmanager webhook body (strict field set)."""

    receiver: str
    status: str
    alerts: list[AlertItem]
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str | None = None
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = None


# In-process alert store (planner's-discretion persistence for DASH-05).
_alerts: list[dict] = []


def _persist_alert(receiver: str, alert: AlertItem) -> None:
    """Append the Agent-K-relevant fields of one alert to the in-process store."""
    _alerts.append(
        {
            "receiver": receiver,
            "alertname": alert.labels.get("alertname"),
            "status": alert.status,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "startsAt": alert.startsAt,
            "fingerprint": alert.fingerprint,
        }
    )


def get_alerts() -> list[dict]:
    """Return the persisted alert records (Phase-5 investigation loop consumes these)."""
    return _alerts


def clear_alerts() -> None:
    """Reset the in-process store (test-support / demo reset)."""
    _alerts.clear()


@router.post("/alerts/webhook")
async def receive_alert(payload: AlertmanagerWebhookPayload) -> dict:
    """Validate -> log (name+status only) -> persist each alert; return count received."""
    for alert in payload.alerts:
        alertname = alert.labels.get("alertname") or payload.groupLabels.get("alertname")
        logger.info("alert received: name=%s status=%s", alertname, alert.status)
        _persist_alert(payload.receiver, alert)
    return {"received": len(payload.alerts)}
