---
phase: 01-telemetry-foundation
plan: 02
subsystem: infra
tags: [signoz, foundry, docker, opentelemetry, observability, clickhouse]

# Dependency graph
requires:
  - phase: 01-telemetry-foundation (plan 01)
    provides: repo scaffolding, .gitignore with pours/ exclusion, .claude/CLAUDE.md tech stack lock
provides:
  - Running self-hosted SigNoz stack (ClickHouse, ClickHouse Keeper, OTel Collector/ingester, query-service+UI, Postgres metastore) via Docker Compose, orchestrated by Foundry
  - Committed casting.yaml (Foundry manifest) + casting.yaml.lock (reproducible-rebuild checksums) — TELE-01 judged deliverable
  - SIGNOZ-RUNBOOK.md documenting primary standup, corrected D-02 fallback, port-hardening caution, memory note, and the "Last 30 minutes" UI pitfall
affects: [01-telemetry-foundation plan 03, phase-02 (RAG app OTel instrumentation), phase-05 (Law 3 self-telemetry), phase-07 (eval harness — clean-machine rebuild timing)]

# Tech tracking
tech-stack:
  added: [foundryctl v0.2.16, signoz/signoz:latest, signoz/signoz-otel-collector:latest, clickhouse/clickhouse-server:25.12.5, clickhouse/clickhouse-keeper:25.12.5, postgres:16 (SigNoz metastore)]
  patterns: ["Foundry gauge -> forge -> cast decoupled pipeline for debuggable infra standup", "casting.yaml (hand-authored) + casting.yaml.lock (generated) committed together; pours/ generated output gitignored"]

key-files:
  created: [casting.yaml, casting.yaml.lock, SIGNOZ-RUNBOOK.md]
  modified: []

key-decisions:
  - "D-01 primary path succeeded on first attempt — no D-02 fallback was needed; foundryctl cast completed the full gauge+forge+deploy pipeline without blocking"
  - "SIGNOZ-RUNBOOK.md documents the CORRECTED D-02 fallback mechanism (forge + manual `docker compose -f pours/deployment/compose.yaml up -d`) per RESEARCH Pitfall 1, since the legacy plain docker-compose.yaml was removed upstream as of SigNoz v0.130.0 — this is a research-driven correction to D-02's literal mechanism, not a re-litigation of its intent"
  - "Port-hardening (T-01-02) is documented as a procedural/network-boundary mitigation, not a container-binding change — Foundry's generated compose config publishes 8080/4317/4318 on the host's 0.0.0.0 interface by default (confirmed via `docker port`), so the actual control is which network the laptop is on, not the Docker port binding itself"

patterns-established:
  - "Foundry gauge -> forge -> cast decoupled sequencing: run each stage separately so a `cast` failure doesn't block confirming whether `forge`'s file generation already succeeded"

requirements-completed: [TELE-01]

coverage:
  - id: D1
    description: "SigNoz stack (ClickHouse, Keeper, OTel ingester, query-service+UI, Postgres metastore) runs self-hosted via Foundry's gauge/forge/cast pipeline"
    requirement: "TELE-01"
    verification:
      - kind: manual_procedural
        ref: "docker ps --format '{{.Names}}\\t{{.Status}}' | grep -i signoz (all containers healthy); curl -sf http://localhost:8080 -> HTTP 200"
        status: pass
    human_judgment: false
  - id: D2
    description: "casting.yaml + casting.yaml.lock committed together, pours/ stays gitignored/untracked"
    requirement: "TELE-01"
    verification:
      - kind: manual_procedural
        ref: "git ls-files casting.yaml casting.yaml.lock (both non-empty); git check-ignore -v pours/deployment/compose.yaml (confirmed ignored)"
        status: pass
    human_judgment: false
  - id: D3
    description: "SIGNOZ-RUNBOOK.md documents corrected D-02 fallback, port-hardening caution, and memory note for a zero-Docker-experience team"
    verification:
      - kind: manual_procedural
        ref: "grep -q 'pours/deployment/compose.yaml' SIGNOZ-RUNBOOK.md && grep -qi 'localhost' SIGNOZ-RUNBOOK.md && grep -qiE 'forge' SIGNOZ-RUNBOOK.md"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-23
status: complete
---

# Phase 01 Plan 02: SigNoz Foundry Standup Summary

**Self-hosted SigNoz stack running via Foundry's gauge->forge->cast pipeline (Docker Compose flavor), with casting.yaml + casting.yaml.lock committed and a corrected-fallback runbook for the team's zero-Docker-experience onboarding.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-23T16:03:00+05:30 (approx, Docker precondition check)
- **Completed:** 2026-07-23T16:27:45+05:30
- **Tasks:** 3 (1 pre-satisfied checkpoint + 2 auto)
- **Files modified:** 3 created (casting.yaml, casting.yaml.lock, SIGNOZ-RUNBOOK.md)

## Accomplishments
- Confirmed Docker Desktop precondition live (Compose v5.3.1, MemTotal ≈ 7.75GB, matching the human's pre-satisfied checkpoint values from the parent conversation)
- Installed `foundryctl` v0.2.16 via the official install script and ran the full `gauge` → `forge` → `cast` pipeline in decoupled order per D-01/Pattern 3 — no D-02 fallback was needed, `cast` succeeded on the first attempt
- SigNoz stack (ClickHouse, ClickHouse Keeper, OTel ingester, query-service+UI, Postgres metastore) is up and healthy; UI reachable at `http://localhost:8080` (HTTP 200)
- Committed `casting.yaml` + `casting.yaml.lock` via scoped `git add` (never `git add -A`), keeping the generated `pours/` directory correctly gitignored — TELE-01 satisfied
- Authored `SIGNOZ-RUNBOOK.md` documenting the primary standup, the CORRECTED D-02 fallback (forge + manual `docker compose up -d` against `pours/deployment/compose.yaml`, explicitly warning the legacy plain docker-compose.yaml was removed upstream as of v0.130.0), the T-01-02 port-hardening caution, the D-03 memory note, and the "Last 30 minutes" default UI-window pitfall

## Task Commits

Each task was committed atomically:

1. **Task 1: Docker Desktop precondition + memory bump to 6-8GB (D-03)** — no commit (checkpoint pre-satisfied by human in parent conversation prior to this dispatch; re-verified live per orchestrator instruction, no code change)
2. **Task 2: Install foundryctl, author casting.yaml, run gauge→forge→cast, commit lock (D-01, D-02)** - `7f1b3cc` (feat)
3. **Task 3: Write SIGNOZ-RUNBOOK.md (corrected D-02 fallback + port hardening + pitfalls)** - `c357726` (docs)

_Note: this plan ran sequentially on the main working tree (not an isolated worktree) per the orchestrator's degrade-to-sequential note — standard commits with hooks, no `--no-verify`._

## Files Created/Modified
- `casting.yaml` - Foundry deployment manifest (apiVersion v1alpha1, mode: docker, flavor: compose)
- `casting.yaml.lock` - Foundry-generated lock file (checksums for deterministic rebuild), 667 lines, auto-generated by `forge`
- `SIGNOZ-RUNBOOK.md` - Standup + corrected-D-02-fallback + port-hardening + pitfalls runbook for the team

## Decisions Made
- D-01 primary path succeeded on the first attempt; D-02 fallback mechanism was not exercised in practice, but is fully documented in the runbook for future use (e.g., if a teammate's machine hits a different failure mode).
- Followed the RESEARCH-driven correction to D-02's literal fallback mechanism (forge + manual compose, not the removed legacy docker-compose.yaml) as instructed by the plan itself — not a new deviation, this was already baked into the plan's `<action>` text.
- Port-hardening (T-01-02) is treated as a documentation/procedural control in the runbook, since Foundry's generated compose config binds to `0.0.0.0` by default (verified via `docker port signoz-signoz-0` / `docker port signoz-ingester-1`) — no compose-level rebind to `127.0.0.1` was attempted, matching the plan's own verification checklist which only requires the runbook to document the caution, not to alter the generated (gitignored) compose file.

## Deviations from Plan

None - plan executed exactly as written. Task 1's checkpoint was pre-satisfied by the human immediately before this dispatch (per the orchestrator's `<pre_satisfied_checkpoint>` note); this executor re-ran the two live sanity checks (`docker compose version`, `docker info --format '{{.MemTotal}}'`) as instructed and confirmed they still agreed with the pre-satisfied values, then proceeded directly to Task 2 without re-blocking.

## Issues Encountered
- The `foundryctl cast` step took several minutes due to first-time Docker image pulls (ClickHouse, ClickHouse Keeper, SigNoz otel-collector, SigNoz UI, Postgres) — this is expected first-run behavior, not a failure. It was run as a backgrounded process and polled via the harness's background-task notification rather than a blocking foreground wait.
- macOS's default shell has no `timeout` command; an initial attempt to time-box `foundryctl cast` with `timeout 180 ...` failed with "command not found" — resolved by using the `run_in_background` execution mode instead, which the harness monitors natively.

## User Setup Required

None - no external service configuration required. Docker Desktop's 6-8GB memory bump (D-03) was already completed by the human immediately prior to this dispatch, per the orchestrator's pre-satisfied-checkpoint note.

## Next Phase Readiness
- SigNoz is running locally and reachable at `http://localhost:8080`; OTLP ingest is available on `4318` (HTTP/protobuf, per the locked stack decision) and `4317` (gRPC, unused).
- `casting.yaml` + `casting.yaml.lock` are committed, giving any teammate (or judge) a reproducible one-command rebuild path (`foundryctl cast -f casting.yaml`), with a documented, tested-mechanism fallback.
- Ready for plan 01-03: end-to-end telemetry verification (OTel Python SDK dual-exporter wiring, FastAPI/SQLAlchemy/logging auto-instrumentation, and confirming traces/logs/metrics actually arrive in this running SigNoz instance).
- No blockers. One open item for later phases: the T-01-02 port-hardening mitigation is currently procedural only (network-boundary discipline); if the team ever needs to expose SigNoz beyond localhost/private-network during the hackathon, a reverse proxy + auth layer would need to be added first — out of scope for this phase.

---
*Phase: 01-telemetry-foundation*
*Completed: 2026-07-23*

## Self-Check: PASSED

All created files verified present on disk (casting.yaml, casting.yaml.lock, SIGNOZ-RUNBOOK.md, this SUMMARY.md). Both task commit hashes (7f1b3cc, c357726) verified present in git log.
