---
phase: 03-failure-injection-dashboard-alerting
plan: 04
status: complete
requirements-completed: [DASH-05]  # code half; SigNoz-UI half is Plan 03-05 (HV-2)
key-files:
  created:
    - app/alerts_webhook.py
    - tests/test_webhook.py
  modified:
    - app/main.py  # include_router + admin routes from 03-01 (this commit stages main.py)
completed: 2026-07-24
---

# Phase 3 Plan 04: Alert Webhook Receiver (DASH-05 code half)

**Built the reusable inbound `POST /alerts/webhook` entrypoint as its own module — a real,
span-wrapped, validated, persisted alert path designed to be the actual Phase-5 Agent K
investigation trigger, not a throwaway. The SigNoz-UI half (building the alert rule + webhook
channel, confirming an end-to-end fire) is human-action Plan 03-05.**

## Accomplishments

- `app/alerts_webhook.py`: narrow strict `AlertItem` / `AlertmanagerWebhookPayload` Pydantic models
  matching SigNoz's Alertmanager-shaped webhook (03-RESEARCH.md Key Finding 2) — a malformed body is
  rejected 422 before processing (no generic parser). In-process store with `_persist_alert` /
  `get_alerts` / `clear_alerts`; `@router.post("/alerts/webhook")` logs only alert name+status
  (never dumps secret-bearing labels/annotations — content-safety, T-03-15) and returns
  `{"received": N}`.
- `app/main.py`: `app.include_router(alerts_webhook.router)` in the step-2 region, before
  `FastAPIInstrumentor.instrument_app`. **This commit stages `app/main.py`, which also carries the
  03-01 `/admin/flags` routes** (shared file — staged once here for a consistent snapshot).
- `tests/test_webhook.py`: 5 tests — valid payload persists + returns count; malformed (missing
  `startsAt`) and missing top-level field both 422 + nothing persisted; secret annotation value
  never appears in logs (caplog); route reachable through the fully-instrumented `app.main.app`.

## Verification

- `pytest tests/test_webhook.py -q` — 5 passed.
- Grep: `include_router(alerts_webhook.router)` precedes `FastAPIInstrumentor.instrument_app` in main.py.
- Full offline suite: 51 passed, 1 skipped (integration), no regressions.

## Phase-3 code-half status

Waves 1–2 (plans 03-01…04) are code-complete and fully offline-tested (29 new Phase-3 tests, 51 total
offline passing). Remaining: **Plan 03-05** (DASH-01/02 dashboard + DASH-05 alert rules built in the
SigNoz UI, exported as JSON, end-to-end webhook fire) is `autonomous:false` and gated on a live SigNoz
stack (HV-2) — not executable in this environment.
