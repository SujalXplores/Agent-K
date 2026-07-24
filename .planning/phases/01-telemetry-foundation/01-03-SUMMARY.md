---
phase: 01-telemetry-foundation
plan: 03
subsystem: infra
tags: [opentelemetry, signoz, foundry, fastapi, otlp, observability]

# Dependency graph
requires:
  - phase: 01-telemetry-foundation (plan 01)
    provides: FastAPI + OTel skeleton (app/main.py, app/telemetry.py) with dual console+OTLP-HTTP exporters
  - phase: 01-telemetry-foundation (plan 02)
    provides: Running self-hosted SigNoz stack via Foundry (casting.yaml/.lock, SIGNOZ-RUNBOOK.md)
provides:
  - "scripts/time-foundry-cast.sh + TELEMETRY-REBUILD-LOG.md with a real measured rebuild duration (TELE-02 closed)"
  - "End-to-end proof that the skeleton's traces, metrics, and trace-correlated logs actually arrive in the SigNoz UI (TELE-03 closed)"
  - "SIGNOZ-RUNBOOK.md §1.5: documented fix for a real infra gap - SigNoz's OTLP receivers never bind until first-run admin/org setup completes"
  - "app/main.py: /healthz now emits an explicit trace-correlated log record per request"
affects: [02-rag-service, phase-04-mcp, phase-07-eval-harness (clean-machine rebuild gate)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["headless SigNoz first-run setup via POST /api/v1/register (no browser needed)", "explicit per-request logging call inside route handlers so OTel LoggingInstrumentor has a real span context to correlate against"]

key-files:
  created: [scripts/time-foundry-cast.sh, TELEMETRY-REBUILD-LOG.md]
  modified: [SIGNOZ-RUNBOOK.md, app/main.py]

key-decisions:
  - "Installed Homebrew python@3.12 + created .venv (this machine had only system Python 3.9 and Homebrew 3.14, neither matching the CLAUDE.md-locked 3.11/3.12 range) before any package install"
  - "Diagnosed and fixed a real cross-plan infra gap: a freshly-cast SigNoz stack looks healthy (containers up, UI 200) but its OTel collector's OTLP receivers never bind until SigNoz's own first-run admin/org setup completes - fixed headlessly via POST /api/v1/register, documented in SIGNOZ-RUNBOOK.md for future rebuilds/teammates/the Day 5-6 clean-machine gate"
  - "Added an explicit logging.info() call inside the /healthz handler (app/main.py) after coordinator's own SigNoz Logs Explorer check found zero request-scoped log records were exporting - uvicorn's own access logger sets propagate=False by default so it never reaches the OTel-wired root logger"

patterns-established:
  - "Headless SigNoz first-run setup: POST /api/v1/register with email/name/orgName/password creates the first admin+org without a browser, unblocking OpAMP agent registration and OTLP receiver binding"
  - "Every FastAPI route handler that needs a trace-correlated log record must call logging.getLogger(__name__).info(...) explicitly inside the handler body - relying on uvicorn's own access log is not sufficient, since it does not propagate to the OTel-instrumented root logger by default"

requirements-completed: [TELE-02, TELE-03]

coverage:
  - id: D1
    description: "scripts/time-foundry-cast.sh times `foundryctl cast` end-to-end and appends a timestamped duration row to TELEMETRY-REBUILD-LOG.md"
    requirement: "TELE-02"
    verification:
      - kind: unit
        ref: "bash -n scripts/time-foundry-cast.sh && grep -q 'foundryctl cast' scripts/time-foundry-cast.sh"
        status: pass
    human_judgment: false
  - id: D2
    description: "A real, measured (not assumed) rebuild duration under 15 minutes (900s) is recorded in TELEMETRY-REBUILD-LOG.md, produced by tearing the stack down and re-running the timing wrapper"
    requirement: "TELE-02"
    verification:
      - kind: integration
        ref: "docker compose -f pours/deployment/compose.yaml down && bash scripts/time-foundry-cast.sh -> 7s recorded, all containers healthy afterward"
        status: pass
    human_judgment: false
  - id: D3
    description: "Traces from the /healthz request are visible in the SigNoz Traces Explorer"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "Coordinator browser-verified Traces Explorer: real GET /healthz + 'GET /healthz http send' spans from agent-k-rag-service, fresh timestamps, status 200"
        status: pass
    human_judgment: true
    rationale: "No SigNoz query API client exists until Phase 4/MCP - this requirement is inherently a human-verified UI check per its own wording ('confirmed visible in the SigNoz UI')."
  - id: D4
    description: "At least one metric emitted by the skeleton is queryable/visible in the SigNoz UI"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "Coordinator browser-verified SigNoz Home onboarding checklist: 'Send your metrics' shows a green checkmark, 'Metrics ingestion is active'"
        status: pass
    human_judgment: true
    rationale: "Same as D3 - inherently a human-verified UI check, no automated SigNoz query client exists yet this phase."
  - id: D5
    description: "Trace-correlated logs from the skeleton are visible in the SigNoz Logs Explorer"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "Coordinator browser-verified Logs Explorer after the app/main.py fix: 'healthz request handled' entries at exact timestamps matching fresh curl calls, correlated to real (non-zero) trace_id/span_id"
        status: pass
    human_judgment: true
    rationale: "Same as D3/D4 - inherently a human-verified UI check. This deliverable required an in-flight fix (Rule 1 bug: /healthz had no logging call) discovered only by the coordinator's own Logs Explorer inspection, since console-exporter output alone did not reveal the gap."
  - id: D6
    description: "The console exporter shows spans locally even if/when the SigNoz UI does not, so generation and delivery are debugged as independent variables (D-06)"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "Console stdout showed real SpanKind.SERVER spans for /healthz both before and after the OTLP delivery fix, proving generation was never the problem - delivery (collector-side OTLP receiver binding) was"
        status: pass
    human_judgment: false

# Metrics
duration: ~52min
completed: 2026-07-23
status: complete
---

# Phase 1 Plan 3: Rebuild-Timing Harness + End-to-End Telemetry Verification Summary

**Measured a 7s SigNoz rebuild (well under the 15-min TELE-02 budget) via a new `scripts/time-foundry-cast.sh` wrapper, and proved traces/metrics/trace-correlated-logs from the FastAPI skeleton all reach the SigNoz UI - after discovering and fixing two real infra/app gaps (SigNoz's OTLP receivers never binding without first-run org setup, and `/healthz` never emitting a request-scoped log).**

## Performance

- **Duration:** ~52 min
- **Started:** 2026-07-23T11:09:00Z (approx, Python 3.12 environment setup)
- **Completed:** 2026-07-23T12:00:59Z
- **Tasks:** 3 (2 auto + 1 checkpoint, checkpoint required a coordinator-driven fix cycle before it could be confirmed)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Provisioned a working Python 3.12 environment (Homebrew `python@3.12` + `.venv`) and installed the pinned `requirements.txt` dependency set, since this machine had neither a stable 3.11 nor 3.12 interpreter pre-installed
- `scripts/time-foundry-cast.sh` times `foundryctl cast -f casting.yaml` end-to-end and appends a `| <timestamp> | <duration>s |` row to `TELEMETRY-REBUILD-LOG.md`; `TELEMETRY-REBUILD-LOG.md` initialized with a markdown table header and a note deferring the authoritative clean-machine measurement to the Day 5-6 gate
- **Discovered and fixed a real infra gap (TELE-03 blocker):** a freshly-cast SigNoz stack reports healthy containers and a 200 from the UI, but its OTel collector's OTLP receivers (4317/4318) never actually bind until SigNoz's own first-run admin/org setup completes - the collector's OpAMP agent registration fails in a loop (`"cannot create agent without orgId"`) and it never gets its real runtime pipeline config. Fixed headlessly via `POST /api/v1/register` (no browser step needed); documented the full repro/fix/verification in `SIGNOZ-RUNBOOK.md` §1.5 for future rebuilds, teammates, and the Day 5-6 clean-machine gate.
- Started the FastAPI skeleton, generated repeated `/healthz` traffic, and confirmed via console stdout that spans were always being generated correctly (`SpanKind.SERVER`, D-06 debugging discipline) - independent of the OTLP delivery problem above
- **Discovered and fixed a second real gap (also TELE-03):** the coordinator's own SigNoz Logs Explorer check found zero request-scoped log records were exporting, even after the OTLP fix above - `/healthz` never called `logging.info(...)`, and the one log line that did export (a one-time startup message) had an all-zero `trace_id` because it ran outside any active span. Added an explicit `logging.getLogger(__name__).info(...)` call inside the `/healthz` handler; verified live that fresh requests now produce log records with real, non-zero `trace_id`/`span_id` matching their request's trace.
- Tore the SigNoz stack down (`docker compose down`) and re-cast it via the timing wrapper to produce a genuine (not warm-no-op) measurement: **7 seconds**, far under the 900s/15min TELE-02 budget. Confirmed the org/setup state persisted across the teardown/recast cycle (Postgres metastore volume survived), so all three OTLP endpoints (traces/metrics/logs) returned HTTP 200 again without repeating the first-run-setup fix.
- Coordinator independently browser-verified all three TELE-03 signals in the live SigNoz UI: real `/healthz` trace spans in Traces Explorer, a green "Metrics ingestion is active" checkmark on the Home page, and trace-correlated `"healthz request handled"` log entries in Logs Explorer matching fresh request timestamps and real trace IDs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create rebuild-timing wrapper + initialize the rebuild log (D-08)** - `3e74c3f` (feat)
2. **Task 2: Verify skeleton traces + logs + metrics are visible in the SigNoz UI (TELE-03)** - checkpoint, two in-flight fix commits required before confirmation: `df86fd8` (fix - SigNoz first-run setup gap) and `26d2b27` (fix - trace-correlated log emission gap); confirmed via coordinator's own browser-based SigNoz UI verification (no separate commit for the confirmation itself)
3. **Task 3: Record a measured rebuild duration under 15 minutes (TELE-02)** - `cbcdc8e` (feat)

**Plan metadata:** committed alongside this SUMMARY (sequential mode on the main working tree - see orchestrator note below)

_Note: this plan ran sequentially on the main working tree (not an isolated worktree) per the orchestrator's degrade-to-sequential note - standard commits with hooks, no `--no-verify`._

## Files Created/Modified
- `scripts/time-foundry-cast.sh` - Bash wrapper timing `foundryctl cast` end-to-end, appends duration+timestamp to the rebuild log
- `TELEMETRY-REBUILD-LOG.md` - Append-only rebuild-duration log; now has one measured row (7s, 2026-07-23T11:58:56Z)
- `SIGNOZ-RUNBOOK.md` - Added §1.5 documenting the required first-run SigNoz admin/org setup step (headless `POST /api/v1/register`) that must run before OTLP delivery works on any freshly-cast stack
- `app/main.py` - `/healthz` now calls `logging.getLogger(__name__).info(...)` inside the handler so it emits a real trace-correlated log record per request

## Decisions Made
- Installed Homebrew `python@3.12` and created a fresh `.venv` before any package install, since neither pre-existing interpreter (system 3.9, Homebrew 3.14) satisfied the CLAUDE.md-locked 3.11/3.12 range - matches the same class of environment gap plan 01-01 hit on a different machine.
- Chose the headless `POST /api/v1/register` fix over asking a human to click through SigNoz's browser signup flow - it's faster, scriptable, and produces the exact same effect (an admin account + org), unblocking the checkpoint without a manual step that the checkpoint protocol tries to avoid.
- Chose to add an explicit `logging.info()` call inside `/healthz` (coordinator's recommended option 1) over reconfiguring uvicorn's access-log propagation (option 2) - minimal, in-scope for a "no /ask or RAG logic yet" skeleton plan, and doesn't touch 01-01's already-committed telemetry wiring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed SigNoz OTLP receivers never binding without first-run setup**
- **Found during:** Task 2 (pre-checkpoint automation - generating traffic and checking OTLP delivery before pausing)
- **Issue:** The SigNoz stack from plan 01-02 looked healthy (`docker ps` all healthy, `curl localhost:8080` → 200), but every OTLP export attempt from the FastAPI skeleton failed with "Connection reset by peer". Root cause: SigNoz's own first-run admin/org setup was never completed (`GET /api/v1/version` showed `"setupCompleted":false`), so the collector's OpAMP agent registration looped on `"cannot create agent without orgId"` and never received its real runtime pipeline config - the OTLP receivers (4317/4318) never actually bound inside the container (confirmed via `/proc/net/tcp` inside `signoz-ingester-1`: no listener on either port before the fix).
- **Fix:** `POST /api/v1/register` with an admin email/name/orgName/password, headlessly (no browser). Confirmed `setupCompleted:true` afterward, and all three OTLP endpoints (`/v1/traces`, `/v1/metrics`, `/v1/logs`) returned HTTP 200 instead of connection-reset.
- **Files modified:** `SIGNOZ-RUNBOOK.md` (documented for future rebuilds/teammates/the Day 5-6 gate)
- **Verification:** Re-ran the three OTLP endpoint curls post-fix (all 200); restarted the FastAPI skeleton and confirmed zero export errors across 8+ `/healthz` calls, versus repeated "Connection reset by peer" / "Failed to export ... batch" errors pre-fix.
- **Committed in:** `df86fd8`

**2. [Rule 1 - Bug] Fixed /healthz never emitting a trace-correlated log record**
- **Found during:** Task 2 (checkpoint - coordinator's own SigNoz Logs Explorer verification, after traces and metrics were already confirmed)
- **Issue:** `/healthz` had no `logging.info()`/similar call - it just returned a status dict. The only log record that ever exported was a one-time startup message logged at module level outside any active span, so its `trace_id` was all-zero (not actually trace-correlated). Fresh `/healthz` requests produced trace spans (visible in Traces Explorer) but zero new log records in Logs Explorer, even on repeated widened-window checks. uvicorn's own access log (which does print `"GET /healthz HTTP/1.1" 200 OK` to console) uses the `uvicorn.access` logger, which sets `propagate: False` by default, so it never reaches the root logger's OTel `LoggingHandler` and is never exported.
- **Fix:** Added `logging.getLogger(__name__).info("healthz request handled")` inside the `/healthz` handler body, where it runs inside the active request span so `LoggingInstrumentor` injects a real, non-zero `trace_id`/`span_id`.
- **Files modified:** `app/main.py`
- **Verification:** Restarted uvicorn, made 3 fresh `/healthz` calls, confirmed each produced a console-and-OTLP-exported log record with a real non-zero `trace_id` (e.g. `5c082502248882af6303cd8c530ec7ca`) matching the request's span. Coordinator then browser-confirmed the same entries live in SigNoz Logs Explorer, timestamps matching the curl calls exactly.
- **Committed in:** `26d2b27`

---

**Total deviations:** 2 auto-fixed (1 blocking-issue fix, 1 bug fix)
**Impact on plan:** Both fixes were necessary for TELE-03 to be genuinely demonstrated rather than superficially "looking fine" (healthy containers, UI 200) while actually not delivering telemetry. No scope creep - both fixes are narrowly targeted at making the phase's own stated requirement (traces/metrics/logs visible in SigNoz UI) actually true, and are documented for reuse by future rebuilds/teammates.

## Issues Encountered
- This machine had no stable Python 3.11/3.12 interpreter pre-installed (only system 3.9 and Homebrew 3.14) - same class of issue plan 01-01 hit on a different machine. Resolved by installing Homebrew `python@3.12` and creating a fresh `.venv` before any package install.
- The two deviations above were only discoverable by actually looking at the SigNoz UI (or its logs) - `docker ps` health checks and `curl localhost:8080` returning 200 gave false confidence that the stack was fully functional. This is a durable lesson for the team: "containers healthy" and "UI reachable" are necessary but not sufficient proof that OTLP delivery and the full signal pipeline actually work.

## User Setup Required

None - both infra gaps found during this plan were fixed programmatically (headless API call + code fix), not via manual browser/UI steps. The admin account created for SigNoz (`admin@agentk.local`) is a local-only, zero-budget hackathon dev credential, not a shipped secret; documented as a reproducible step in `SIGNOZ-RUNBOOK.md` §1.5 rather than as a one-off manual action.

## Next Phase Readiness
- Phase 1 (telemetry-foundation) is now fully complete: TELE-01 (plan 01-02, SigNoz self-hosted via Foundry with committed `casting.yaml`/`.lock`), TELE-02 (this plan, measured 7s rebuild), and TELE-03 (this plan, traces/metrics/trace-correlated-logs all confirmed live in the SigNoz UI) are all satisfied.
- `app/main.py` and `app/telemetry.py` are ready for Phase 2 to extend with the real `/ask` route and pgvector retrieval logic - no re-wiring needed, and the new `logging.info()`-per-handler pattern established here should be followed by every future route that needs a trace-correlated log record.
- `SIGNOZ-RUNBOOK.md` §1.5 (first-run setup) is now a required step for any teammate standing up the stack fresh, and specifically for the Day 5-6 clean-machine-rebuild gate in Phase 7 - without it, TELE-02's rebuild-timing script would "succeed" (containers healthy) while OTLP delivery silently doesn't work.
- No blockers for Phase 2. One thing worth carrying forward: "containers healthy + UI reachable" is not sufficient evidence of a working telemetry pipeline on this stack - always confirm the OTLP endpoints themselves respond (or check the Logs/Traces Explorer directly) before treating a SigNoz standup as done.

---
*Phase: 01-telemetry-foundation*
*Completed: 2026-07-23*

## Self-Check: PASSED

- FOUND: scripts/time-foundry-cast.sh
- FOUND: TELEMETRY-REBUILD-LOG.md
- FOUND: SIGNOZ-RUNBOOK.md
- FOUND: app/main.py
- FOUND: .planning/phases/01-telemetry-foundation/01-03-SUMMARY.md
- FOUND commit: 3e74c3f (Task 1)
- FOUND commit: df86fd8 (Task 2 - fix, SigNoz first-run setup gap)
- FOUND commit: 26d2b27 (Task 2 - fix, trace-correlated log gap)
- FOUND commit: cbcdc8e (Task 3)
