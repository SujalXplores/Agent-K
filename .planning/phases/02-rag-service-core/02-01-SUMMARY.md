---
phase: 02-rag-service-core
plan: 01
subsystem: database
tags: [pgvector, postgres, sqlalchemy, alembic, sentence-transformers, asyncpg, docker-compose]

# Dependency graph
requires:
  - phase: 01-telemetry
    provides: app/telemetry.py module shape (DEFAULT_* constants + load_dotenv + os.getenv pattern) mirrored by app/embeddings.py and app/db.py
provides:
  - A running rag-postgres (pgvector/pgvector:pg16) container with the vector extension installed and a documents table (vector(384) embedding column) applied via Alembic migration 0001
  - app/embeddings.py — local sentence-transformers embedding module (EMBEDDING_DIM=384, embed_text, embed_texts)
  - app/db.py — async SQLAlchemy engine + session factory + pgvector type registration + SQLAlchemyInstrumentor wiring
  - app/models.py — Document model (id, doc_id, title, body, embedding vector(384))
  - Alembic scaffold (alembic.ini, alembic/env.py, alembic/versions/0001_create_documents.py) with the migration actually applied to a live database
affects: [02-02-corpus-seeding, 02-04-retrieval-endpoint]

# Tech tracking
tech-stack:
  added: [sqlalchemy==2.0.51, greenlet==3.5.4, asyncpg==0.31.0, pgvector==0.5.0, alembic==1.18.5, sentence-transformers==5.6.0, openai==2.46.0, opentelemetry-instrumentation-sqlalchemy==0.65b0, httpx, pytest, pytest-asyncio]
  patterns: ["DEFAULT_* constant + load_dotenv()/os.getenv setup-function shape (mirrors app/telemetry.py)", "single EMBEDDING_DIM source of truth imported by both models.py and the Alembic migration", "pgvector asyncpg registration via event.listens_for(engine.sync_engine, 'connect') + register_vector"]

key-files:
  created: [docker-compose.yaml, app/embeddings.py, app/db.py, app/models.py, alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0001_create_documents.py]
  modified: [requirements.txt, .env.example]

key-decisions:
  - "Used pgvector.asyncpg.register_vector (not pgvector.psycopg) since the project's connection URL is postgresql+asyncpg:// — psycopg's submodule doesn't apply to this driver and doesn't even export the function needed."
  - "Added greenlet==3.5.4 as an explicit pin — SQLAlchemy's async engine requires it for the sync-to-async bridge used by Alembic's async_engine_from_config, but it was never declared as a direct dependency."
  - "Rebuilt the scratch verify-venv (/tmp/agentk-p2) on /opt/homebrew/bin/python3.12 rather than plain `python -m venv`, which resolves to system Python 3.9.6 on this machine and silently drops fastapi==0.139.2 from pip's candidate list."

patterns-established:
  - "Datastore compose file (docker-compose.yaml) is separate from the Foundry-generated pours/ compose for SigNoz — never touch the gitignored/regenerable Foundry output for app-specific services."
  - "Alembic resolves sqlalchemy.url from the DATABASE_URL env var inside env.py, never hardcoded in alembic.ini, so no credentials live in a committed file."

requirements-completed: [RAG-01, RAG-02]

coverage:
  - id: D1
    description: "pgvector-enabled Postgres container running and reachable, with the vector extension and documents table (vector(384) embedding) applied via a real Alembic migration against the live database"
    requirement: "RAG-01"
    verification:
      - kind: integration
        ref: "docker compose exec rag-postgres psql -U agentk -d agentk -c '\\dx vector' && -c '\\d documents' (manual command, output captured in this run)"
        status: pass
      - kind: integration
        ref: "alembic upgrade head && alembic current (reports 0001 (head); re-run is a no-op, confirming idempotency)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Local sentence-transformers embedding module produces normalized 384-dim vectors with zero external API calls"
    requirement: "RAG-02"
    verification:
      - kind: integration
        ref: "python -c \"from app.embeddings import embed_text, EMBEDDING_DIM; ...\" against /tmp/agentk-p2 venv with full requirements.txt installed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Async SQLAlchemy engine registers pgvector on connect and is instrumented for free DB spans"
    requirement: "RAG-01"
    verification:
      - kind: unit
        ref: "python -c \"from app.models import Document, Base; ...\" column-presence assertion (Task 2 verify block)"
        status: pass
    human_judgment: true
    rationale: "Column presence and import success were verified programmatically, but actual OTel span emission from SQLAlchemyInstrumentor was not exercised end-to-end in this plan (no live query issued against the instrumented engine yet) — defer full trace verification to 02-04 when the retrieval query path exists."

duration: 62min
completed: 2026-07-23
status: complete
---

# Phase 02 Plan 01: RAG Datastore Foundation Summary

**pgvector-enabled Postgres (docker-compose), async SQLAlchemy engine with pgvector asyncpg registration + OTel instrumentation, Document model, local sentence-transformers embeddings (384-dim), and Alembic migration 0001 applied to the live database.**

## Performance

- **Duration:** ~62 min total across two sessions (Tasks 1-2 in prior session, Task 3 in this continuation run ~15 min)
- **Started:** 2026-07-23T17:53:00Z (approx, Task 1 start per prior session)
- **Completed:** 2026-07-23T20:02:36Z
- **Tasks:** 3/3
- **Files modified:** 9 (8 created, 1 modified across the plan: requirements.txt, docker-compose.yaml, .env.example, app/embeddings.py, app/db.py, app/models.py, alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0001_create_documents.py)

## Accomplishments

- Stood up a pgvector-enabled Postgres container (`rag-postgres`, image `pgvector/pgvector:pg16`) via a dedicated `docker-compose.yaml`, separate from the Foundry-managed SigNoz compose.
- Built `app/embeddings.py`: a local, zero-network-call `sentence-transformers/all-MiniLM-L6-v2` embedding module producing normalized 384-dim vectors (`EMBEDDING_DIM`, `get_model()`, `embed_text()`, `embed_texts()`).
- Built `app/db.py`: async SQLAlchemy engine (`postgresql+asyncpg://`), pgvector type registration via `event.listens_for(engine.sync_engine, "connect")` + `pgvector.asyncpg.register_vector`, session factory, and `SQLAlchemyInstrumentor` wiring for free DB spans.
- Built `app/models.py`: `Document` model (`id`, `doc_id`, `title`, `body`, `embedding` typed `Vector(EMBEDDING_DIM)`), sourcing its dimension from `app.embeddings.EMBEDDING_DIM` as the single source of truth.
- Authored and **applied** Alembic migration `0001_create_documents.py` against the live `rag-postgres` database: `CREATE EXTENSION IF NOT EXISTS vector` followed by the `documents` table. Confirmed via `psql`: `vector` extension v0.8.5 installed, `documents.embedding` typed `vector(384)`.
- Confirmed idempotency: re-running `alembic upgrade head` after reaching head is a no-op (no migration re-applied).

## Task Commits

Each task was committed atomically:

1. **Task 1: pinned deps, docker-compose.yaml, .env.example, app/embeddings.py** - `0aa1c8c` (feat)
2. **Task 2: async engine, Document model, Alembic migration file** - `20ddb46` (feat)
3. **Task 3: apply migration to live database** - no independent file diff (the migration application itself is a DB-side effect, not a code change); the one code fix required to unblock it is captured separately below.

**Deviation fix (part of Task 3):** `50ece84` (fix) — pinned missing `greenlet==3.5.4` dependency.

**Plan metadata:** (this commit, pending) - `docs(02-01): complete RAG datastore foundation plan`

## Files Created/Modified

- `docker-compose.yaml` - `rag-postgres` service (pgvector/pgvector:pg16, port 5432, healthcheck)
- `app/embeddings.py` - local embedding module, `EMBEDDING_DIM=384`
- `app/db.py` - async engine, pgvector asyncpg registration, SQLAlchemyInstrumentor wiring
- `app/models.py` - `Document` model with `vector(384)` embedding column
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` - async Alembic scaffold reading `DATABASE_URL` from env, never hardcoded
- `alembic/versions/0001_create_documents.py` - migration creating the `vector` extension + `documents` table; **applied to the live database in this run**
- `requirements.txt` - added `sqlalchemy`, `greenlet`, `asyncpg`, `pgvector`, `alembic`, `sentence-transformers`, `openai`, `opentelemetry-instrumentation-sqlalchemy`, `httpx`, `pytest`, `pytest-asyncio`
- `.env.example` - added `DATABASE_URL`, `LLM_PROVIDER`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`, `EMBEDDING_MODEL`

## Decisions Made

- Used `pgvector.asyncpg.register_vector` (not `pgvector.psycopg`) since the connection driver is asyncpg — fixed in Task 2's commit (`20ddb46`), reconfirmed correct in this run.
- Added `greenlet==3.5.4` as an explicit pin (Rule 3 — blocking issue): SQLAlchemy's async engine requires it for the greenlet-based sync/async bridge used internally by `async_engine_from_config`, but nothing in `requirements.txt` declared it directly, so `alembic upgrade head` failed with `ValueError: the greenlet library is required to use this function`. Verified `greenlet==3.5.4` exists on PyPI (T-02-SC gate) before pinning.
- Reused the scratch verify-venv at `/tmp/agentk-p2` (built on `/opt/homebrew/bin/python3.12`) rather than recreating it, per the documented anti-pattern (plain `python -m venv` resolves to system Python 3.9.6 on this machine).
- Did not restart Docker Desktop or touch the running SigNoz stack — `docker compose up -d rag-postgres` started cleanly from the already-cached local image (digest `1d533553fefe`) with zero network pulls, resolving the prior session's blocker without any Docker-level intervention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pinned missing `greenlet` dependency**
- **Found during:** Task 3 (`alembic upgrade head`)
- **Issue:** `alembic upgrade head` failed with `ValueError: the greenlet library is required to use this function` — SQLAlchemy's async engine needs `greenlet` for its sync-to-async bridge, but it was never declared in `requirements.txt` (was pulled in transitively before, or simply missed when Task 2 added the async engine).
- **Fix:** Verified `greenlet==3.5.4` is a legitimate PyPI package (real, long-established dependency of SQLAlchemy's asyncio support — not a supply-chain risk), installed it into the scratch venv, and added the pin to `requirements.txt` immediately after `sqlalchemy==2.0.51`.
- **Files modified:** `requirements.txt`
- **Verification:** `alembic upgrade head` succeeded afterward; `alembic current` reports `0001 (head)`; full `pip install -r requirements.txt` re-run confirms no unresolved packages.
- **Committed in:** `50ece84` (separate commit, per continuation-run instructions, since Tasks 1-2 were already committed and this defect was discovered while executing Task 3)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for the migration to run at all against an async engine; no scope creep — this is a missing transitive dependency pin, not new functionality.

## Issues Encountered

- The prior session's blocker (`docker pull pgvector/pgvector:pg16` failing on `unexpected EOF` due to unreliable network) was already resolved before this run started — the image was pre-cached locally (digest `1d533553fefe`, 640MB) and `docker compose up -d rag-postgres` started without attempting any network pull, confirmed by watching the compose output (no "Pulling" step appeared).
- No other issues — Tasks 1 and 2's prior work (`0aa1c8c`, `20ddb46`) were spot-checked against this run (container health, model import, migration file contents) and found correct with no further defects beyond the greenlet pin.

## User Setup Required

None - no external service configuration required. (`GROQ_API_KEY` / `CEREBRAS_API_KEY` / `GEMINI_API_KEY` remain empty in `.env.example` for the user to fill in locally when Plan 02-03/02-04's LLM calls are exercised, but that is documented in those plans' SUMMARYs, not this one.)

## Next Phase Readiness

- The live `rag-postgres` database now has a real `documents` table with `vector(384)` embeddings and the `vector` extension installed — Plan 02-02 (corpus seeding) can insert real rows via `app.db` + `app.models.Document` + `app.embeddings.embed_text` immediately.
- Plan 02-04 (retrieval endpoint) can rely on `app/db.py`'s `SQLAlchemyInstrumentor` wiring for free DB spans under the hand-written `rag.retrieval` span, and on `EMBEDDING_DIM=384` as the single dimension source of truth.
- No blockers remaining for this plan. `docker-compose.yaml`'s `rag-postgres` service should be left running for 02-02's seed script to target.

---
*Phase: 02-rag-service-core*
*Completed: 2026-07-23*

## Self-Check: PASSED

All 11 claimed files found on disk (docker-compose.yaml, app/embeddings.py, app/db.py, app/models.py, alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0001_create_documents.py, requirements.txt, .env.example, 02-01-SUMMARY.md). All 3 claimed commits found in git log (`0aa1c8c`, `20ddb46`, `50ece84`).
