# Phase 1: Telemetry Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-21
**Phase:** 1-telemetry-foundation
**Areas discussed:** SigNoz install fallback trigger, Skeleton service scope, OTLP/console exporter switching, Rebuild-time measurement

---

## SigNoz Install Fallback Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Time-boxed fallback | Attempt Foundry first; if not working after 2-3 hours, fall back to plain `docker-compose.yaml`, retrofit `casting.yaml`/`.lock` later | ✓ |
| Only on hard blocker | Never fall back unless Foundry literally crashes or has no usable docs | |
| Never fall back | Push through with Foundry regardless of time cost, since it's a judged deliverable | |

**User's choice:** Deferred to Claude's recommendation — time-boxed fallback (2-3 hours), matching CLAUDE.md's own documented "Stack Patterns by Variant" guidance.
**Notes:** User has zero prior Docker/OTel/SigNoz experience and asked Claude to recommend the best path for the project rather than choose among options themselves.

---

## Skeleton Service Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Disposable smoke-test | A throwaway script proving telemetry arrives, deleted before Phase 2 | |
| Real reusable scaffold | `app/main.py` FastAPI service with OTel wiring done correctly, extended directly by Phase 2 | ✓ |

**User's choice:** Deferred to Claude's recommendation — real reusable scaffold, to avoid redoing OTel instrumentation wiring twice.
**Notes:** Same deferral rationale as above.

---

## OTLP/Console Exporter Switching

| Option | Description | Selected |
|--------|-------------|----------|
| Env-var toggle | One exporter active at a time, switched via env var | |
| Always dual-export | Console + OTLP both active simultaneously, no toggle needed | ✓ |

**User's choice:** Deferred to Claude's recommendation — always dual-export, since silent OTLP delivery failure was research-flagged as the top Day-1 pitfall.
**Notes:** Same deferral rationale as above.

---

## Rebuild-Time Measurement

| Option | Description | Selected |
|--------|-------------|----------|
| Manual stopwatch | Team times the rebuild by hand and writes a note | |
| Scripted measurement | Small wrapper script times `foundryctl cast` and logs to `TELEMETRY-REBUILD-LOG.md` | ✓ |

**User's choice:** Deferred to Claude's recommendation — scripted measurement, for a reproducible, judge-verifiable artifact.
**Notes:** Same deferral rationale as above.

---

## Claude's Discretion

- Exact directory structure inside `app/` (e.g., whether OTel setup lives in a separate module from `main.py`)
- Shell script vs. Python script for the rebuild-timing wrapper
- Fine-tuning SigNoz Docker Compose resource limits beyond the 6-8GB Docker Desktop floor

## Deferred Ideas

None — discussion stayed within Phase 1 scope. All four gray areas were resolved via Claude's recommendation at the user's explicit request, given the team's stated lack of prior experience with Docker/OTel/SigNoz/Foundry.
