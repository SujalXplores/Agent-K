---
phase: 01-telemetry-foundation
plan: 01
subsystem: infra
tags: [fastapi, opentelemetry, otlp, python-dotenv, telemetry]

# Dependency graph
requires: []
provides:
  - "Reusable FastAPI + OTel scaffold (app/main.py, app/telemetry.py) that later phases import and extend"
  - "setup_telemetry() function wiring dual (console + OTLP-HTTP) exporters for traces, metrics, and logs"
  - "GET /healthz endpoint proving the skeleton boots and is instrumented"
  - "Pinned requirements.txt for the FastAPI + OTel dependency set"
  - ".env.example template and .gitignore hygiene for secrets/build artifacts"
affects: [02-rag-service, "future phases that add FastAPI routes"]

# Tech tracking
tech-stack:
  added: [fastapi==0.139.2, "uvicorn[standard]==0.51.0", python-dotenv==1.2.2, opentelemetry-api==1.44.0, opentelemetry-sdk==1.44.0, opentelemetry-exporter-otlp-proto-http==1.44.0, opentelemetry-instrumentation-fastapi==0.65b0, opentelemetry-instrumentation-logging==0.65b0]
  patterns: ["dual-exporter-always-on (console + OTLP, no toggle)", "instrument_app() called AFTER route registration", "single shared Resource across traces/metrics/logs providers"]

key-files:
  created: [requirements.txt, .env.example, app/__init__.py, app/telemetry.py, app/main.py]
  modified: [.gitignore]

key-decisions:
  - "Used stable Python 3.12.10 (installed via winget mid-execution) instead of the only pre-existing local interpreter (3.12.0a1 alpha), per coordinator direction after the Task 1 checkpoint"
  - "Removed the manual LoggingHandler attachment in setup_telemetry() (Rule 1 fix) — opentelemetry-instrumentation-logging's LoggingInstrumentor auto-attaches its own handler to the registered LoggerProvider, so keeping both caused every log record to export twice"

patterns-established:
  - "Dual-exporter-always-on: every OTel provider (Tracer/Meter/Logger) registers both a console exporter and an OTLP-HTTP exporter, never a single exporter behind an env toggle (D-06)"
  - "FastAPI instrumentation ordering: routes must be registered before FastAPIInstrumentor.instrument_app(app) is called, or those routes are never wrapped"
  - "OTLP exporters imported only from opentelemetry.exporter.otlp.proto.http.* (HTTP/protobuf, port 4318) — never the gRPC transport (D-07)"

requirements-completed: [TELE-03]

coverage:
  - id: D1
    description: "FastAPI skeleton boots and GET /healthz returns 200 {\"status\":\"ok\"}"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "uvicorn app.main:app --port 8000 && curl -sf localhost:8000/healthz"
        status: pass
    human_judgment: false
  - id: D2
    description: "A request to /healthz produces a real OTel span printed to console stdout via ConsoleSpanExporter, independent of OTLP delivery"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "uvicorn app.main:app then curl /healthz, inspect console stdout for SpanKind.SERVER span"
        status: pass
    human_judgment: false
  - id: D3
    description: "Console AND OTLP-HTTP exporters registered simultaneously for all three signals, no env-var toggle; OTLP exporters imported only from the HTTP/protobuf package family (no gRPC)"
    requirement: "TELE-03"
    verification:
      - kind: manual_procedural
        ref: "grep app/telemetry.py for add_span_processor (x2) and metric_readers (x2 entries); grep for opentelemetry.exporter.otlp.proto.grpc (0 matches)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Package legitimacy of all 8 pinned PyPI dependencies confirmed by a human before first pip install"
    requirement: "TELE-03"
    verification: []
    human_judgment: true
    rationale: "Legitimacy confirmation is inherently a human judgment call (T-01-SC threat), not something a passing automated check can substitute for — resolved via explicit coordinator approval at the Task 1 checkpoint."

# Metrics
duration: ~15min
completed: 2026-07-22
status: complete
---

# Phase 1 Plan 1: Telemetry Foundation - FastAPI + OTel Skeleton Summary

**Reusable FastAPI skeleton with always-on dual (console + OTLP-HTTP) OpenTelemetry exporters for traces/metrics/logs, wired via `setup_telemetry()` in `app/telemetry.py`, no `/ask` or RAG logic yet.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-22T09:18:00Z (approx, worktree creation)
- **Completed:** 2026-07-22T09:33:08Z
- **Tasks:** 3 (1 checkpoint + 2 auto)
- **Files modified:** 6 (5 created, 1 modified)

## Accomplishments
- Package-legitimacy checkpoint cleared for all 8 pinned PyPI dependencies (T-01-SC), with an explicit interpreter-swap directive (stable Python 3.12.10 instead of the only locally available 3.12.0a1 alpha) addressed before proceeding
- `requirements.txt` pins the exact 8-package FastAPI + OTel dependency set (no `opentelemetry-instrumentation-sqlalchemy` — correctly deferred to Phase 2)
- `.gitignore` extended (preserving the pre-existing `.planning/research/.cache/` rule) to ignore `.env`, `pours/`, and standard Python build artifacts
- `app/telemetry.py`'s `setup_telemetry()` wires a shared `Resource` and dual console+OTLP-HTTP exporters across `TracerProvider`, `MeterProvider`, and `LoggerProvider` — always on, no toggle (D-06), HTTP/protobuf only on port 4318, never gRPC (D-07)
- `app/main.py` boots, serves `GET /healthz` returning `{"status":"ok"}`, and calls `FastAPIInstrumentor.instrument_app(app)` strictly after route registration
- Verified live: `curl -sf localhost:8000/healthz` returns `{"status":"ok"}` and the console exporter prints a real `SpanKind.SERVER` span for that request; OTLP delivery attempts fail with connection-refused (expected — no collector running yet, verified separately in plan 01-03)

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy sanity check before first pip install** - checkpoint, no commit (human-verify gate; resolved via coordinator "approved" message)
2. **Task 2: Repo scaffold — requirements.txt, .gitignore, .env.example, app package** - `df51f8b` (feat)
3. **Task 3: OTel dual-exporter wiring (app/telemetry.py) + FastAPI skeleton (app/main.py)** - `8f81fd6` (feat)

**Plan metadata:** committed alongside this SUMMARY (worktree mode — see note below)

## Files Created/Modified
- `requirements.txt` - Pins the 8-package FastAPI + OTel dependency set
- `.gitignore` - Adds `.env`, `pours/`, `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.pytest_cache/` while preserving the pre-existing `.planning/research/.cache/` line
- `.env.example` - OTLP HTTP/protobuf endpoint (port 4318) and service-name placeholders, no secrets
- `app/__init__.py` - Empty, makes `app.main:app` importable by uvicorn
- `app/telemetry.py` - `setup_telemetry()`: shared `Resource`, dual console+OTLP-HTTP exporters for traces/metrics/logs
- `app/main.py` - FastAPI app, `/healthz` route, correctly-ordered instrumentation calls

## Decisions Made
- Local machine had no stable Python 3.11/3.12 interpreter (only 2.7, 3.13, and 3.12.0a1 alpha) at plan start; provisioned a `.venv` on the alpha as a stopgap, flagged it in the Task 1 checkpoint, and the coordinator directed a switch to stable Python 3.12.10 (installed via winget) before proceeding — venv was recreated on the stable interpreter before any package install.
- Followed RESEARCH.md Pattern 1 for the logging provider setup but diverged from its literal code (manually attaching a `LoggingHandler`) once live testing showed it caused duplicate log export — see Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate LoggingHandler causing every log record to export twice**
- **Found during:** Task 3 (live `python -c "import app.main"` verification)
- **Issue:** RESEARCH.md Pattern 1's logging example calls for manually attaching a `LoggingHandler(logger_provider=...)` to the root logger inside `setup_telemetry()`. When `app/main.py` then calls `LoggingInstrumentor().instrument(set_logging_format=True)`, that instrumentor auto-attaches its *own* `LoggingHandler` bound to the same globally-registered `LoggerProvider` (confirmed in the installed `opentelemetry-instrumentation-logging` source — `enable_log_auto_instrumentation` defaults to `true`). With both handlers present, every log record was exported twice through both the console and OTLP processors.
- **Fix:** Removed the manual `LoggingHandler` instantiation/attachment from `setup_telemetry()`, relying solely on `LoggingInstrumentor`'s auto-attached handler (which correctly picks up the `LoggerProvider` registered earlier in the same startup sequence).
- **Files modified:** `app/telemetry.py`
- **Verification:** Re-ran `python -c "import app.main"` and confirmed the startup log line now prints exactly once (was twice before the fix); root logger now shows exactly one `LoggingHandler` after both `setup_telemetry()` and `LoggingInstrumentor().instrument(...)` have run.
- **Committed in:** `8f81fd6` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary for correctness — duplicate log export would have doubled every log record delivered to SigNoz in later phases. No scope creep; the fix only removes code, it adds nothing beyond what `LoggingInstrumentor` already does automatically.

## Issues Encountered
- Local machine's only pre-existing Python 3.x interpreters were 3.13 (explicitly discouraged for week 1 per CLAUDE.md) and a 3.12.0a1 pre-release alpha — no stable 3.11/3.12 was present. Flagged at the Task 1 checkpoint; resolved when the coordinator installed stable Python 3.12.10 via winget mid-session and directed the venv be recreated on it before any package install.

## User Setup Required

None - no external service configuration required. (Docker/SigNoz setup is intentionally deferred to sibling plans 01-02 and 01-03, which require Docker Desktop to be installed — not yet available on this machine per the plan's context note.)

## Next Phase Readiness
- `app/telemetry.py` and `app/main.py` are ready for plan 01-02 (SigNoz via Foundry/Docker) and 01-03 (rebuild-timing + SigNoz UI verification) to build on — once a collector is listening on `localhost:4318`, the already-wired OTLP exporters need no code changes to start delivering.
- No blockers for Phase 2 (`/ask` route + pgvector retrieval) — `setup_telemetry()` is designed to be imported and called without re-wiring, and new routes only need to be registered above the existing `FastAPIInstrumentor.instrument_app(app)` call.
- Concern carried forward: this machine's Python interpreter availability was fragile at plan start (no stable 3.11/3.12 pre-installed) — now resolved (3.12.10 stable installed), but worth confirming on other teammates' machines during Day 1 onboarding per PROJECT.md's ramp-up concerns.

---
*Phase: 01-telemetry-foundation*
*Completed: 2026-07-22*
