---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: "Phase 3 planned (5 plans, plan-checker PASS) — ready for /gsd:execute-phase"
last_updated: "2026-07-24T13:19:33.467Z"
last_activity: 2026-07-24 — Phase 02 gap-closure plans 02-05..02-07 executed directly; see 02-05/06/07-SUMMARY.md
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 15
  completed_plans: 10
  percent: 29
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-20)

**Core value:** Every claim Agent K publishes is backed by resolvable SigNoz evidence, and every action it takes passes a code-enforced safety gate — nothing is trust-the-model, everything is prove-it-in-telemetry.
**Current focus:** Phase 02 — rag-service-core

## Current Position

Phase: 02 (rag-service-core) — GAP CLOSURE APPLIED
Plan: 7 of 7 executed (02-05, 02-06, 02-07 all landed — waves 4-6 complete)
Status: All 3 failed must-haves from 02-VERIFICATION.md fixed and re-tested directly (no gsd-execute-phase, per explicit user instruction): pgvector adapter conflict removed (SC-1/RAG-01), setup_db_instrumentation() wired + proven by scripts/probe_ask_spans.py (SC-3/RAG-03/D-07), misleading span-count assertion corrected, CR-03/CR-04 hardened in app/llm.py, REQUIREMENTS.md ledger corrected. Full suite: 25/25 passing (18 original + 3 live-DB integration + 4 llm.py credential/completion-guard tests). RAG-01/RAG-03 remain marked "Reopened" and RAG-04 "Needs human verification" in REQUIREMENTS.md until a formal re-verification pass and HV-1/HV-2 (below) are performed — this session fixed and tested the code but did not run gsd-verifier.
Last activity: 2026-07-24 — Phase 02 gap-closure plans 02-05..02-07 executed directly; see 02-05/06/07-SUMMARY.md

Progress: [██████████] 100% of gap-closure plans (formal re-verification still outstanding)

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P02 | 25min | 3 tasks | 3 files |
| Phase 01 P03 | 52min | 3 tasks | 4 files |
| Phase 02 P03 | 6min | 2 tasks | 4 files |
| Phase 02 P01 | 62min | 3 tasks | 9 files |
| Phase 02 P02 | 9min | 2 tasks | 3 files |
| Phase 02 P04 | 12min | 2 tasks | 7 files |
| Phase 02 P05 (gap) | ~15min | 2 tasks | 3 files |
| Phase 02 P06 (gap) | ~15min | 3 tasks | 4 files |
| Phase 02 P07 (gap) | ~10min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 7-phase horizontal-layer structure (per research SUMMARY.md), phases execute in strict dependency order except Phase 4 (MCP), which is parallelizable with Phases 2-3 but must land before Phase 5.
- [Roadmap]: DASH-01/02/05 (Service Health, Incident Context, Alerts) placed in Phase 3 (data exists once RAG+failure-injection exist); DASH-03/04 (Agent Health, Action Audit Trail) deferred to Phase 7 (data doesn't exist until Agent K/Law 2 are built).
- [Rollback mechanism]: Rollback now executes via a separate, privilege-isolated `deployer` sidecar (sole Docker-socket holder, one authenticated `POST /rollback`, hardcoded target/command, concurrency lock) instead of Agent K editing docker-compose directly on the host. Agent K never holds the Docker socket — its worst-case blast radius is one HTTP call. Adopted from the `main` branch plan for a structurally-enforced (not convention-based) Law 2 sandbox. The sidecar has no dependency on the agent pipeline, so its skeleton can be scaffolded early to de-risk it. Updated across PROJECT.md (req + Key Decision), REQUIREMENTS.md (LAW2-03/04), ROADMAP.md (Phase 6), and all four research docs.
- [Phase 01-02]: SIGNOZ-RUNBOOK.md documents the CORRECTED D-02 fallback (forge + manual docker compose against pours/deployment/compose.yaml), not the removed legacy docker-compose.yaml
- [Phase 01]: SigNoz's OTLP receivers never bind on a freshly-cast stack until first-run admin/org setup completes (POST /api/v1/register) - documented in SIGNOZ-RUNBOOK.md sec 1.5 as a required step for every fresh rebuild
- [Phase 01]: FastAPI route handlers must call logging.getLogger(__name__).info(...) explicitly to emit a trace-correlated log record - uvicorn's own access log does not propagate to the OTel-instrumented root logger
- [Phase 02]: Single record_llm_call_attributes helper (app/observability.py) is the sole source of truth for gen_ai.*/agentk.*/rag.* attribute names, reused unchanged by Phase 5 self-telemetry — Prevents attribute-name drift breaking Phase 3/7 dashboard queries (D-06)
- [Phase 02]: Added greenlet==3.5.4 pin - SQLAlchemy async engine requires it for Alembic's async_engine_from_config bridge, was missing from requirements.txt
- [Phase 02]: rag-postgres (pgvector/pgvector:pg16) live with vector extension + documents table (vector(384)) applied via Alembic migration 0001, unblocking 02-02 corpus seeding
- [Phase 02]: Corpus authored via a one-off (non-committed) Python generator script producing 72 real hand-authored docs for fictional B2B SaaS product Flowdeck, across the six D-01 topic areas with D-02 length variety
- [Phase 02]: Seed script idempotency implemented as delete-all-then-insert inside one transaction (corpus-on-disk is source of truth), not ON CONFLICT upsert
- [Phase 02]: POST /ask wired end-to-end (retrieve -> build_prompt -> generate), emitting exactly three GenAI-instrumented spans (rag.retrieval, rag.prompt_construction, chat) per call — Completes RAG-01/RAG-03 - the phase's headline deliverable; tracer acquired fresh per-call (not cached at import) in app/rag.py to keep test isolation working, mirroring app/llm.py's established pattern
- [Phase 02 gap-closure]: 02-VERIFICATION.md (2026-07-23) found POST /ask returned HTTP 500 against the live DB — app/db.py registered BOTH the pgvector.asyncpg connect-level codec AND relied on the pgvector.sqlalchemy Vector ORM type on Document.embedding; the two serialization paths are mutually exclusive and asyncpg rejected the already-serialized parameter. Removed the connect-level codec (app/db.py); the ORM type alone is sufficient for the asyncpg dialect via SQLAlchemy.
- [Phase 02 gap-closure]: setup_db_instrumentation() (app/db.py) was defined but never called anywhere — SQLAlchemyInstrumentor never activated, so the D-07 "free DB span" was silently absent. Wired into app/main.py's startup sequence, after setup_telemetry() and after route registration.
- [Phase 02 gap-closure]: tests/test_ask.py's `assert len(spans)==3` passed for an accidental reason — FastAPIInstrumentor binds its tracer at app.main import time, before the in_memory_exporter fixture monkeypatches the provider, so framework/DB spans never reached it. Added scripts/probe_ask_spans.py, which registers an observable TracerProvider BEFORE importing app.main (in a fresh subprocess) to measure the true production span set (9 spans on the healthy path incl. the DB span) — this is now the pattern for any future "prove telemetry is really emitted" check, not just a grep for the instrumentation call.
- [Phase 02 gap-closure]: asyncpg connections are bound to the asyncio event loop that created them — mixing asyncio.run() (module-level prechecks), pytest-asyncio-managed tests, and TestClient-driven sync tests against the SAME SQLAlchemy async engine in one test process causes "another operation is in progress" / "attached to a different loop" errors. Fixed in tests/test_integration_rag.py via explicit engine.dispose() calls between loop boundaries (test-harness-only; production runs on a single event loop and is unaffected). Any future live-DB integration test added to this suite must follow the same dispose-between-tests pattern.
- [Phase 02 gap-closure]: app/llm.py hardened per 02-REVIEW.md CR-03/CR-04 — get_client() now raises MissingProviderKeyError (not a silent OPENAI_API_KEY fallback) on a missing/empty {PROVIDER}_API_KEY; generate() raises EmptyCompletionError (not a bare IndexError/500) on an empty choices list, and normalizes a None message.content to "" so the D-04 response contract can't be violated at serialization time.
- [Phase 02 gap-closure]: this gap-closure work (02-05/06/07) was executed by directly editing files and running pytest/verification probes per the existing 02-05/06/07-PLAN.md task specs, WITHOUT invoking /gsd-execute-phase or any other gsd-* skill, per explicit user instruction. REQUIREMENTS.md's RAG-01/RAG-03 are marked "Reopened" (not "Complete") because closing them per the plan's own success criteria requires a formal gsd-verifier re-verification pass, which was not run this session. RAG-04 remains "Needs human verification" (HV-1: live provider credential exercise; HV-2: confirm a trace actually renders in the SigNoz UI) — neither is possible in this environment.

### Pending Todos

- [Phase 02]: Run a formal re-verification pass (goal-backward, against 02-VERIFICATION.md's original 15 must-haves) now that 02-05/06/07 have landed and 25/25 tests pass, before considering Phase 2 fully complete and moving to Phase 3.
- [Phase 02]: HV-1 — set a real GROQ_API_KEY (then CEREBRAS_API_KEY, then GEMINI_API_KEY) via LLM_PROVIDER and confirm each provider genuinely serves a grounded /ask response with no source-code edit between runs. Closes RAG-04.
- [Phase 02]: HV-2 — bring up the live SigNoz stack (SIGNOZ-RUNBOOK.md sec 1.5 first-run setup), POST /ask once, and confirm the trace (rag.retrieval, rag.prompt_construction, chat, plus the SQLAlchemy SELECT span) actually renders in the SigNoz UI. Confirms SC-3's "in SigNoz" half.

### Blockers/Concerns

- [Roadmap]: One team member unavailable Jul 24-26 (days 5-7 of the 7-day window) coincides with the heaviest, most safety-critical phases (5, 6, 7 — 32/50 requirements, including both remaining Laws and the full eval harness). Front-load Phase 5 Law 3 telemetry and Phase 6 policy-schema drafting; treat Day 5-6 clean-machine-rebuild and Groq-rate-limit checks as go/no-go gates before Phase 7 eval runs.
- [Roadmap]: Team has zero prior Docker/OTel/SigNoz experience — Phase 1 ramp-up risk is real; research flags ClickHouse memory starvation (bump Docker Desktop memory to 6-8GB) and silent OTLP delivery failures (always debug via console-exporter first) as the top two Day 1 pitfalls.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-07-24T13:19:33.423Z
Stopped at: Phase 3 planned (5 plans, plan-checker PASS) — ready for /gsd:execute-phase
Resume file: 
.planning/phases/03-failure-injection-dashboard-alerting/03-01-PLAN.md
