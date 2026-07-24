---
phase: 03
slug: failure-injection-dashboard-alerting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (existing, from Phase 2) |
| **Config file** | `tests/conftest.py` (in_memory_exporter fixture + live-DB helpers) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~30–60 seconds (live-DB integration tests dominate) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Populated by the planner as PLAN.md tasks are written; each task's `<automated>`
> verify command lands here. Codeable requirements (FLAG-01..06, webhook receiver)
> get automated pytest coverage using the `in_memory_exporter` span-assertion pattern
> and the `scripts/probe_ask_spans.py` subprocess pattern for "prove the telemetry is
> really emitted" checks. Manual-only rows (DASH-01/02/05 SigNoz-UI build) go in the
> Manual-Only section below.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD by planner_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_flags.py` — flag store + admin endpoint (FLAG-01), token auth
- [ ] `tests/test_injection.py` — each fault injector changes emitted telemetry (FLAG-02..05, FLAG-06 marker span present/absent)
- [ ] `tests/test_webhook.py` — `POST /alerts/webhook` parses Alertmanager-shaped payload, persists it
- [ ] Extend `tests/conftest.py` only if new shared fixtures are needed (flag-reset between tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Service Health + Incident Context dashboard sections render live | DASH-01, DASH-02 | Hand-built in the SigNoz UI; requires a live Foundry stack (HV-2) | Follow SIGNOZ-RUNBOOK.md Phase-3 steps; build panels; export dashboard JSON to repo; confirm panels populate after a `/ask` load + a fault toggle |
| SLO/burn-rate/cost alert fires webhook end-to-end | DASH-05, Success Criterion 4 | SigNoz alert rule + webhook channel hand-built in UI; needs live stack | Configure alert rule + webhook channel targeting `/alerts/webhook`; toggle retry-storm; confirm the receiver logs a real SigNoz payload |
| Deployment-marker span appears in traces for scenarios 1–2 only | FLAG-06, Success Criterion 2 | Visual confirmation in SigNoz trace explorer (automated span-emission test covers the code side) | After HV-2, toggle each scenario; confirm `deployment.marker` span present for 1–2, absent for 3–4 |

*Automated tests cover the code side of every FLAG requirement; the SigNoz-UI half is manual and gated on HV-2, mirroring Phase 2's HV-1/HV-2 pattern.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
