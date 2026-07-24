# Phase 03 Discussion Log

**Date:** 2026-07-24
**Phase:** Failure Injection + Dashboard + Alerting
**Mode:** discuss (default)

_Human-reference audit record only. Not consumed by downstream agents — see 03-CONTEXT.md for the decisions that flow into research/planning._

## Gray areas presented

User selected all four for discussion:
1. Flag store & admin API
2. Deployment markers (FLAG-06)
3. Alert webhook receiver
4. Manual-UI vs code split

## Q&A

### Area 1 — Flag store & admin API (FLAG-01)
- **Options:** Single endpoint + token (recommended) / Per-flag path endpoints / Let planner decide
- **Chosen:** Single endpoint + token
- **Notes:** `POST /admin/flags` {name, enabled} + `GET /admin/flags`; in-memory dict read fresh per
  request; `X-Admin-Token` header from env, open when env empty (local-demo friendly). Routes must be
  registered before FastAPI instrumentation.

### Area 2 — Deployment markers (FLAG-06)
- **Options:** SigNoz API call on toggle (recommended) / service.version resource bump / Let researcher decide
- **Chosen:** SigNoz API call on toggle
- **Notes:** Explicit SigNoz deployment/change-event call when scenarios 1-2 toggle on; 3-4 skip it.
  service.version-bump approach rejected (resource fixed at process start, conflicts with no-restart).
  Exact SigNoz endpoint/payload flagged as the top research item.

### Area 3 — Alert webhook receiver (DASH-05)
- **Options:** Reusable Agent K stub (recommended) / Throwaway logging endpoint / Let planner decide
- **Chosen:** Reusable Agent K stub
- **Notes:** Real `POST /alerts/webhook` in its own module, validates+logs+persists, designed as the
  Phase 5 investigation trigger. De-risks the reduced-capacity Phase 5 window.

### Area 4 — Manual-UI vs code split (DASH-01/02/05)
- **Options:** Code now, UI as runbook (recommended) / Block on live SigNoz first / Let planner decide
- **Chosen:** Code now, UI as runbook
- **Notes:** All code (flags, injectors, marker emitter, webhook receiver, tests) built now without a
  live stack; dashboard + alert rules captured as runbook human-actions with exported JSON committed
  once SigNoz is up. Phase not blocked on HV-2.

## Deferred ideas
- DASH-03 (Agent Health) and DASH-04 (Action Audit Trail) — deferred to Phase 7 per roadmap.

## Claude's discretion (skipped areas)
- None — user discussed all four gray areas.
