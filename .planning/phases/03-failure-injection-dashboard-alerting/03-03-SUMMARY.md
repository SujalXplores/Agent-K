---
phase: 03-failure-injection-dashboard-alerting
plan: 03
status: complete
requirements-completed: [FLAG-03, FLAG-05]
key-files:
  created:
    - tests/test_injection_llm_db.py
  modified:
    - app/llm.py
    - app/db.py
completed: 2026-07-24
---

# Phase 3 Plan 03: LLM/DB-tier Fault Injectors (retry-storm, pool-exhaustion)

**Injected the two remaining fault scenarios: retry-storm (FLAG-03, `app/llm.py`) and
DB-pool-exhaustion (FLAG-05, `app/db.py`). Retry-storm's signal is a COST/CALL-RATE anomaly that
stays HTTP 200 on eventual success; pool-exhaustion uses an application-level semaphore so a
concurrent checkout fails without touching the real engine/pool (no-restart preserved).**

## Accomplishments

- `app/llm.py`: constants `NORMAL_TIMEOUT_S`/`RETRY_STORM_TIMEOUT_S`/`MAX_RETRIES`. Inside the `chat`
  span, `generate()` reads `flags.is_enabled("retry_storm")` fresh; ON → lowered `timeout=` kwarg +
  up to `MAX_RETRIES` attempts (breaks on success, re-raises on genuine exhaustion), OFF → exactly one
  attempt at the normal timeout. Stamps `AGENTK_LLM_RETRY_COUNT` (the DASH-05 cost-alert signal).
  Existing usage-normalization / `record_llm_call_attributes` / empty-choices guard untouched.
- `app/db.py`: module-level `_pool_exhaustion_semaphore = asyncio.Semaphore(1)` + `POOL_ACQUIRE_TIMEOUT_S`.
  When `db_pool_exhaustion` is ON, `get_session` gates checkout via `asyncio.wait_for(acquire, ...)`;
  a concurrent second checkout raises `TimeoutError("simulated DB pool exhaustion")`, logs it at ERROR,
  and flags `AGENTK_DB_POOL_EXHAUSTED` on the current span. OFF path unchanged; **no** second
  `create_async_engine`, **no** pgvector connect-level codec (header rule intact).
- `tests/test_injection_llm_db.py`: 5 tests — retry OFF single attempt + normal timeout; retry ON
  retries-then-succeeds (attempts>1, still returns an `LlmResult`) + lowered timeout; retry ON
  exhaustion propagates; pool OFF concurrent checkouts succeed; pool ON second concurrent checkout
  raises + logs.

## Verification

- `pytest tests/test_injection_llm_db.py -q` — 5 passed.
- Full offline suite still green (no regression to `generate()` / `get_session` healthy paths).
