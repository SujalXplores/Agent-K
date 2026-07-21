---
phase: 1
slug: telemetry-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None yet exists in this greenfield repo. `pytest` + `pytest-asyncio` are the project's locked choice (CLAUDE.md) but no config file exists yet, and this phase has no business logic to unit test. |
| **Config file** | none — no framework bootstrap needed this phase (first real test files arrive in Phase 2 when `/ask` endpoint logic exists) |
| **Quick run command** | N/A this phase — see smoke/manual commands per requirement below |
| **Full suite command** | N/A this phase — see smoke/manual commands per requirement below |
| **Estimated runtime** | N/A — this phase is infra standup + a thin skeleton with no unit-testable logic |

---

## Sampling Rate

- **After every task commit:** Run the smoke check relevant to that task (see Per-Task Verification Map) — `git ls-files` check for TELE-01 tasks, wrapper-script dry-run for TELE-02 tasks, `curl` + console-exporter stdout check for TELE-03 tasks
- **After every plan wave:** Run the full manual verification pass — rebuild timing + SigNoz UI check together
- **Before `/gsd-verify-work`:** All three requirements' checks must pass together: TELE-01 (files committed + `cast` succeeds), TELE-02 (logged duration < 15 min in `TELEMETRY-REBUILD-LOG.md`), TELE-03 (SigNoz UI shows traces/metrics/logs)
- **Max feedback latency:** Immediate — every check in this phase is a synchronous command or a single UI look, not a background test run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner assigns) | TBD | TBD | TELE-01 | — | `casting.yaml`/`casting.yaml.lock` tracked by git, not ignored | smoke | `git ls-files casting.yaml casting.yaml.lock` (both non-empty) && `foundryctl cast -f casting.yaml && docker ps` | ❌ Wave 0 | ⬜ pending |
| TBD (planner assigns) | TBD | TBD | TELE-02 | — | Rebuild duration measured and logged, not assumed | smoke (scripted) | `scripts/time-foundry-cast.sh` then `grep` last row of `TELEMETRY-REBUILD-LOG.md` for duration < 900s | ❌ Wave 0 | ⬜ pending |
| TBD (planner assigns) | TBD | TBD | TELE-03 | — | Traces/metrics/logs from the FastAPI skeleton visible in SigNoz UI; console exporter shows spans independent of OTLP delivery | manual-only | `curl localhost:8000/healthz` to generate traffic, then check console stdout, then check SigNoz Traces Explorer / Logs Explorer / a metrics panel at `localhost:8080` (widen "Last 30 minutes" window if needed) | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/time-foundry-cast.sh` (or `.py`) — covers TELE-02, does not yet exist
- [ ] `TELEMETRY-REBUILD-LOG.md` — needs to be initialized with a markdown table header (`| Timestamp (UTC) | Duration |` / `|---|---|`) before the first script run
- [ ] No `pytest` infrastructure needed yet for this phase specifically — first real test files arrive in Phase 2

*Nothing else — existing infrastructure (none) is sufficient because this phase has no unit-testable business logic; all checks are infra smoke tests or manual UI verification by design (per RESEARCH.md's Validation Architecture).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Traces, metrics, and logs from the FastAPI skeleton are visible in the SigNoz UI | TELE-03 | No SigNoz query API client exists yet (that's Phase 4/MCP's job) — this requirement is inherently a human-verified UI check per its own wording ("confirmed visible in the SigNoz UI") | 1. Start the FastAPI skeleton. 2. `curl localhost:8000/healthz`. 3. Confirm a span prints to console (stdout). 4. Open SigNoz UI at `localhost:8080`. 5. Check Traces Explorer for the request span. 6. Check Logs Explorer for a trace-correlated log line. 7. Check a basic metrics panel/query. 8. If nothing appears, widen the default "Last 30 minutes" time window before concluding delivery is broken. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < immediate (synchronous checks only)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
