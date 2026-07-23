---
phase: 02-rag-service-core
plan: 05
subsystem: db
tags: [pgvector, sqlalchemy, asyncpg, pytest-integration]
gap_closure: true
requirements-completed: [RAG-01, RAG-02]
completed: 2026-07-24
status: complete
---

# Phase 2 Gap Closure Plan 5: Fix pgvector adapter conflict + add live-DB integration tests

**Removed the connection-level `pgvector.asyncpg.register_vector` codec in `app/db.py` that conflicted with the `pgvector.sqlalchemy.Vector` ORM type and made every parameterized vector query raise `asyncpg.exceptions.DataError`; added the phase's first tests that execute real pgvector SQL against the live `rag-postgres` container.**

## Root cause

`app/models.py`'s `Document.embedding` uses `pgvector.sqlalchemy.Vector(EMBEDDING_DIM)`, whose bind processor already serializes a Python list into Postgres's `'[...]'` text form. `app/db.py` additionally registered the `pgvector.asyncpg` codec on every new connection via a `connect` event listener — that codec expects a raw list/ndarray and rejected the already-serialized string, so every parameterized vector-bound query (i.e. every retrieval) raised `DataError`. The two serialization paths are mutually exclusive; only the ORM type is needed for the asyncpg dialect via SQLAlchemy.

## Changes

- `app/db.py`: removed `_register_vector_type` (the `@event.listens_for(..., "connect")` listener), the `pgvector.asyncpg` import, and the `sqlalchemy.event` import. Rewrote the module docstring to name `app/models.py`'s column type as the sole serialization path and explicitly warn against reintroducing a second one.
- `tests/conftest.py`: added `pytest_configure(config)` registering the `integration` pytest marker.
- `tests/test_integration_rag.py` (new): live-database tests, skipped (not errored) when the DB is unreachable. `test_retrieve_executes_real_pgvector_query_against_live_corpus` calls `app.rag.retrieve()` with a real locally-embedded query against the real seeded corpus. `test_ask_returns_grounded_sources_against_live_db` posts to `/ask` through a `TestClient` with no `get_session` override, so it hits the live DB (only the third-party LLM call is stubbed).

## Deviation from plan (env fix, not scope creep)

Task 2's live tests initially failed with `sqlalchemy.exc.InterfaceError: another operation is in progress` / `RuntimeError: ... attached to a different loop`. Cause: asyncpg connections are bound to the asyncio event loop that created them; the module-level corpus-count precheck (`asyncio.run(...)`), the `pytest-asyncio`-managed async test, and the synchronous `TestClient`-driven test each run on a different event loop, so a pooled connection left over from one loop broke the next. Fixed by disposing the engine's connection pool (`await get_engine().dispose()`) at the end of the precheck's own loop and via an autouse `_dispose_engine_between_tests` fixture after every test in the module — forces a fresh connection on the next loop. This is a test-harness-only fix; no production code path is affected (the FastAPI app runs on a single event loop in production).

## Verification

- Live retrieval probe: `retrieve(AsyncSessionLocal(), "How do I rotate an API key?", top_k=3)` → `['rotate-api-key', 'api-key-scopes-permissions', 'revoke-lost-api-key']` (previously raised `DataError`).
- `python -m pytest tests/test_integration_rag.py -q -m integration` → 2 passed (this plan's two tests; a third was added by 02-06).
- `python -m pytest tests/ -q` → 20 passed (18 pre-existing + 2 new), no regression.
- Skip path: `DATABASE_URL` pointed at an unreachable host → 1 skipped, not errored.
- `app/db.py` surface check: no `_register_vector_type`/`register_vector`/`event` attributes remain; `get_engine`/`get_session`/`setup_db_instrumentation` still callable.

## Closes

SC-1 / RAG-01 (POST /ask returns 200 with grounded sources against the live DB) and re-proves RAG-02 at query time (not just seed time).
