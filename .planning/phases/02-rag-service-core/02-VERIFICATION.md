---
phase: 02-rag-service-core
verified: 2026-07-23T20:50:57Z
status: gaps_found
score: 11/15 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "A request to POST /ask returns a generated answer grounded in docs retrieved from pgvector (ROADMAP SC-1, RAG-01)"
    status: failed
    reason: "POST /ask returns HTTP 500 against the live, correctly-seeded database. app/db.py registers the pgvector asyncpg codec (pgvector.asyncpg.register_vector) on every connection while app/models.py uses the pgvector SQLAlchemy type (pgvector.sqlalchemy.Vector). SQLAlchemy's Vector bind processor already serializes the list to the '[...]' text form, and the registered asyncpg codec then rejects that string because it expects a list/ndarray. Every parameterized vector query therefore raises asyncpg.exceptions.DataError. Reproduced end-to-end via FastAPI TestClient against the real DB; failure occurs at retrieval, before any LLM call, so it is NOT an API-key problem."
    artifacts:
      - path: "app/db.py"
        issue: "Lines 35-43: the @event.listens_for(_engine.sync_engine, 'connect') _register_vector_type listener calling dbapi_connection.run_async(register_vector) conflicts with the SQLAlchemy-level Vector type and breaks every vector-bound query."
      - path: "tests/conftest.py"
        issue: "fake_session fixture makes session.execute an AsyncMock, so the pgvector SQL is never compiled or executed. No test can detect this failure."
      - path: "tests/test_rag.py"
        issue: "Asserts the shape of the constructed Select statement (_limit_clause/_order_by_clauses) rather than executing it — proves SQL construction, never SQL execution."
    missing:
      - "Remove the register_vector connect listener from app/db.py (the pgvector.sqlalchemy.Vector type already handles serialization for the asyncpg dialect), OR keep the codec and stop using the SQLAlchemy Vector type — the two registration paths are mutually exclusive."
      - "At least one integration test that executes a real pgvector cosine-distance SELECT against a live database instead of an AsyncMock session."
  - truth: "Every /ask call produces distinct retrieval, prompt-construction, and generation spans in SigNoz carrying GenAI semantic-convention attributes (ROADMAP SC-3, RAG-03, D-07)"
    status: failed
    reason: "In production a real POST /ask emits 5 spans, of which only ONE of the three required GenAI spans exists: rag.retrieval (status ERROR). rag.prompt_construction and chat are never created because retrieval raises first. The three spans are only all present when the SC-1 blocker is removed. Additionally the D-07 test asserting this (tests/test_ask.py::test_ask_produces_exactly_three_genai_spans, 'assert len(spans) == 3') does not measure production span count — FastAPIInstrumentor binds its tracer at import time to the real provider, so the 4 FastAPI framework spans never reach the monkeypatched in_memory_exporter. Measured production count with a correctly-bound provider is 7 spans on the healthy path, not 3."
    artifacts:
      - path: "app/main.py"
        issue: "The /ask handler has no error handling, so a retrieval failure aborts the pipeline and suppresses the prompt-construction and generation spans entirely."
      - path: "tests/test_ask.py"
        issue: "Lines 43-48: `assert len(spans) == 3` passes for an accidental reason (provider-binding timing), not because production emits exactly 3 spans."
    missing:
      - "Fix the SC-1 retrieval blocker so all three spans are reachable on the request path."
      - "Re-derive the D-07 span assertion so it filters by span name against the production tracer provider, rather than asserting a total count under a partially-bound provider."
      - "Confirm the three spans are actually visible in the SigNoz UI (no evidence of any Phase 2 trace reaching SigNoz exists in the phase artifacts)."
  - truth: "The async SQLAlchemy engine is registered with opentelemetry-instrumentation-sqlalchemy so retrieval queries emit free DB spans (02-01 must-have, D-07)"
    status: failed
    reason: "CR-02 independently confirmed at runtime. app/db.py defines setup_db_instrumentation() but nothing ever calls it — grep across the whole repo finds only the definition (app/db.py:62) and a prose mention in an app/rag.py docstring (app/rag.py:59). SQLAlchemyInstrumentor therefore never activates. Measured: healthy-path /ask emits 7 spans with zero DB spans; calling setup_db_instrumentation() manually raises this to 9 spans, adding the 'connect' and 'SELECT' DB spans. The D-07 'hand-written spans layer on top of the free DB spans' design is unimplemented at runtime."
    artifacts:
      - path: "app/db.py"
        issue: "setup_db_instrumentation() (lines 62-70) is defined but orphaned — never imported or invoked."
      - path: "app/main.py"
        issue: "Application startup calls setup_telemetry() and FastAPIInstrumentor.instrument_app(app) but never setup_db_instrumentation()."
    missing:
      - "Call setup_db_instrumentation() during app startup in app/main.py (before or alongside FastAPIInstrumentor.instrument_app)."
      - "A verification step that asserts a DB span is emitted for the retrieval query, not just that the instrumentation function exists."
behavior_unverified_items:
  - truth: "Switching the LLM provider env var (Groq / Cerebras / Gemini Flash) changes which provider serves requests with no code change (ROADMAP SC-4, RAG-04)"
    test: "Set GROQ_API_KEY in .env and POST /ask; confirm a real generated answer returns. Then set LLM_PROVIDER=cerebras with CEREBRAS_API_KEY and repeat; then LLM_PROVIDER=gemini with GEMINI_API_KEY. Confirm each request is genuinely served by the named provider (check the chat span's gen_ai.response.model matches that provider's model family)."
    expected: "Each provider returns a real grounded answer, and gen_ai.system / gen_ai.request.model / gen_ai.response.model on the chat span reflect the selected provider — with no source-code edit between runs."
    why_human: "No provider credential is available in this environment, so no live provider call could be made. Client construction was verified programmatically for all three providers (correct base_url, model, and {PROVIDER}_API_KEY lookup, plus a KeyError on an unknown provider), but 'serves requests' asserts runtime behavior against a third-party endpoint that presence checks cannot see."
human_verification:
  - test: "Set a provider credential and exercise POST /ask against each of groq / cerebras / gemini via LLM_PROVIDER, with no code change between runs."
    expected: "Each provider returns a real grounded answer; the chat span's gen_ai.* attributes name the selected provider."
    why_human: "No provider API key is available in this environment; a live third-party call cannot be made or guessed."
  - test: "After the SC-1 and SC-3 blockers are fixed, run the RAG service against the live SigNoz stack, issue a POST /ask, and open the trace in the SigNoz UI."
    expected: "A single trace shows the POST /ask server span with rag.retrieval, rag.prompt_construction, and chat as distinct child spans, each carrying its rag.*/gen_ai.* attributes, plus the SQLAlchemy SELECT span underneath rag.retrieval."
    why_human: "No Phase 2 artifact contains evidence that any /ask trace has ever reached the SigNoz UI. SC-3 says 'in SigNoz', and only a human looking at the UI can confirm ingestion and rendering end-to-end."
---

# Phase 2: RAG Service Core Verification Report

**Phase Goal:** The monitored RAG application answers support questions end-to-end, with every step of the pipeline individually visible in SigNoz as GenAI-instrumented spans.
**Verified:** 2026-07-23T20:50:57Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal has two halves. The **substrate half is genuinely built and provably real**: a live pgvector database holds 72 locally-embedded synthetic support docs, the retrieval logic returns semantically correct results, the three-span instrumentation design is correct, and the provider abstraction is clean. The **end-to-end half does not hold**: `POST /ask` returns HTTP 500 against the real database because of a pgvector adapter conflict in `app/db.py`, which means the application does not answer support questions end-to-end and does not emit the three required spans on a real request.

This was invisible to the phase's own verification because every test mocks the database session, so the pgvector SQL is never compiled or executed. All 18 tests pass while production is broken.

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | **SC-1** — `POST /ask` returns a generated answer grounded in docs retrieved from pgvector | ✗ FAILED | `TestClient(app).post("/ask", ...)` against live `rag-postgres` → **HTTP 500**, `DBAPIError: asyncpg.exceptions.DataError: invalid input for query argument $1: '[-0.0409...' (expected list or ndarray)`. Fails at retrieval, before the LLM. |
| 2 | **SC-2** — pgvector store contains 50-200 synthetic docs embedded locally, no external embedding API | ✓ VERIFIED | Live DB: `72 rows, 72 distinct doc_id, 72 non-null embeddings`; `vector_dims = 384` for all 72; `72 distinct embedding vectors`; self dot-product `1.0000` (unit-normalized, i.e. real model output). No external embedding client imported in `app/embeddings.py` or `scripts/seed_corpus.py`. Seed script re-run live → `corpus seeding complete: 72 docs`, count still 72/72 (idempotent). |
| 3 | **SC-3** — Every `/ask` call produces distinct retrieval, prompt-construction, and generation spans in SigNoz with GenAI semconv attributes | ✗ FAILED | Production span capture on a real `/ask`: **5 spans, only `rag.retrieval` (status ERROR)** — `rag.prompt_construction` and `chat` never created. Healthy-path measurement (blocker removed) shows 7 spans, not the 3 the D-07 test asserts. No evidence any trace reached SigNoz. |
| 4 | **SC-4** — Switching `LLM_PROVIDER` changes which provider serves requests, no code change | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Config switch proven for all three: groq→`api.groq.com/openai/v1` + `llama-3.1-8b-instant`; cerebras→`api.cerebras.ai/v1` + `llama3.1-8b`; gemini→`generativelanguage.googleapis.com/v1beta/openai/` + `gemini-2.0-flash`; unset→groq default; `bogus`→`KeyError`. **But no live provider call is possible (no credential)** — "serves requests" is unexercised. |
| 5 | pgvector Postgres container running and reachable at `DATABASE_URL` | ✓ VERIFIED | `docker compose ps` → `rag-postgres Up 48 minutes (healthy)`; `pgvector/pgvector:pg16` in `docker-compose.yaml`; real async connections established from `app/db.py`. |
| 6 | `documents` table exists with `vector` extension and a `vector(384)` embedding column | ✓ VERIFIED | `pg_extension` → `vector 0.8.5`; `vector_dims(embedding)` → `384` for all rows; `alembic_version` → `0001`; migration executes `CREATE EXTENSION IF NOT EXISTS vector` and `sa.Column("embedding", Vector(384), nullable=False)`. |
| 7 | Embedding module produces 384-dim vectors from a local model with zero external API calls | ✓ VERIFIED | `app/embeddings.py` uses `SentenceTransformer(...).encode(..., normalize_embeddings=True)`; `EMBEDDING_DIM = 384`; no `openai`/`cohere`/`requests` import. Live `embed_text()` produced a 384-float vector used in a real query. |
| 8 | Async engine registered with `opentelemetry-instrumentation-sqlalchemy` so retrieval queries emit free DB spans (D-07) | ✗ FAILED | **CR-02 confirmed.** `setup_db_instrumentation()` never called anywhere (`grep` → definition at `app/db.py:62` + a docstring mention at `app/rag.py:59` only). Measured: 7 spans / **0 DB spans** as shipped; 9 spans with `connect` + `SELECT` when called manually. |
| 9 | Seed script loads the corpus into `documents` with locally-computed embeddings | ✓ VERIFIED | Ran `python -m scripts.seed_corpus` live → `corpus seeding complete: 72 docs`; row count 72/72 after. |
| 10 | Each seeded doc has a non-null `vector(384)` embedding and stable `doc_id` + `title` | ✓ VERIFIED | `count(embedding) = 72`, `count(distinct doc_id) = 72`; retrieval returned `doc_id`/`title` pairs (`rotate-api-key` / "Rotating an API key without downtime"). |
| 11 | A single OpenAI-compatible client module is the only place any provider is constructed (RAG-04) | ✓ VERIFIED | `grep -rn "OpenAI(" app/ scripts/` → exactly one construction site, `app/llm.py:90` inside `get_client()`. No provider-specific SDK, no LiteLLM proxy. |
| 12 | One shared `record_llm_call_attributes` helper sets the gen_ai attributes, reusable by Phase 5 | ✓ VERIFIED | `app/observability.py:67` defines it; `app/llm.py:142` is the sole caller; all attribute-name strings are module constants. Observed on a live chat span: `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `agentk.llm.provider`, `agentk.llm.estimated_cost_usd`. |
| 13 | Response body is `{answer, sources:[{doc_id,title}]}` per D-04 | ✓ VERIFIED | Healthy-path response: `{"answer":"stubbed answer","sources":[{"doc_id":"rotate-api-key","title":"Rotating an API key without downtime"},...]}`. `app/schemas.py` models match exactly. |
| 14 | Retrieval span sets `rag.retrieval.top_k` and `rag.retrieval.doc_count` from the shared constants | ✓ VERIFIED | Captured live: `rag.retrieval => {'rag.retrieval.top_k': 3, 'rag.retrieval.doc_count': 3}`; `app/rag.py` imports both names from `app/observability.py`. |
| 15 | The `/ask` route is registered before `FastAPIInstrumentor.instrument_app(app)` | ✓ VERIFIED | `app/main.py`: route at line 42, `instrument_app` at line 69. Confirmed at runtime — FastAPI produced `POST /ask` server spans. |

**Score:** 11/15 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `docker-compose.yaml` | pgvector Postgres service | ✓ VERIFIED | `pgvector/pgvector:pg16`, healthcheck present, container healthy. |
| `app/embeddings.py` | Local embedding helper + `EMBEDDING_DIM` | ✓ VERIFIED | 53 lines; exports `EMBEDDING_DIM`, `get_model`, `embed_text`, `embed_texts`; imported by `models.py`, `rag.py`, `seed_corpus.py`. |
| `app/db.py` | Async engine, session factory, pgvector registration, OTel instrumentation | ⚠️ **HARMFUL** | Engine and session factory work, but the pgvector connect listener actively breaks every vector query, and the OTel instrumentation function is orphaned. This file is the source of 2 of the 3 blockers. |
| `app/models.py` | `Document` model with `vector(384)` column | ✓ VERIFIED | `Vector(EMBEDDING_DIM)` derived from the single source of truth; matches live schema. |
| `alembic/versions/0001_create_documents.py` | Migration creating the extension and table | ✓ VERIFIED | Applied (`alembic_version = 0001`). Note: hardcodes `Vector(384)` rather than importing `EMBEDDING_DIM`, contradicting the `app/embeddings.py` docstring. |
| `data/corpus/` | 50-200 synthetic docs, 6 topics, length variety | ✓ VERIFIED | 72 `.md` files, 6 topic dirs × 12; body length 244–1926 chars (D-02 variety confirmed in the DB). |
| `scripts/seed_corpus.py` | Idempotent local-embedding loader | ✓ VERIFIED | Ran live successfully; delete-then-insert in one transaction. |
| `app/observability.py` | Shared gen_ai/agentk attribute helper | ✓ VERIFIED | Single source of truth for all attribute names; wired and exercised. |
| `app/llm.py` | Single provider client factory + instrumented `generate()` | ✓ VERIFIED | Sole `OpenAI(...)` construction site; `chat` span with full gen_ai attributes observed. |
| `app/rag.py` | `retrieve()` + `build_prompt()` with their spans | ⚠️ HOLLOW | Logic and spans are correct and produce excellent retrieval when the `db.py` conflict is removed, but as shipped `retrieve()` always raises against the real DB. |
| `app/schemas.py` | D-04 Pydantic contract | ✓ VERIFIED | `AskRequest` (bounded 1–2000 chars), `Source`, `AskResponse`. |
| `app/main.py` | `POST /ask` wiring, registered before instrumentation | ⚠️ ORPHANED WIRING | Route ordering correct, but never calls `setup_db_instrumentation()`. |
| `tests/test_ask.py` | Three-span + D-04 assertions | ⚠️ MISLEADING | Passes, but the span-count assertion does not reflect production and the DB is fully mocked. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `app/db.py` | `DATABASE_URL` | `os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL)` | ✓ WIRED | Live connection made using the env var; `.env.example` line 5 declares it. |
| `app/models.py` | `app/embeddings.py` | `Vector(EMBEDDING_DIM)` | ✓ WIRED | Import present, live column is `vector(384)`. |
| `app/db.py` | pgvector adapter | `event.listens_for(..., 'connect')` + `register_vector` | ✗ **BROKEN** | The link exists but is *harmful* — it is the direct cause of the SC-1 failure. A/B test: with listener → `DataError`; without listener → returns `['rotate-api-key','api-key-scopes-permissions','revoke-lost-api-key']`. |
| `app/db.py` | `SQLAlchemyInstrumentor` | `setup_db_instrumentation()` | ✗ NOT WIRED | Function never called; 0 DB spans in production. |
| `scripts/seed_corpus.py` | `app/embeddings.py` | `embed_texts()` | ✓ WIRED | Executed live during a real seed run. |
| `scripts/seed_corpus.py` | `documents` table | `AsyncSessionLocal` + `Document` | ✓ WIRED | 72 rows written live. |
| `app/llm.py` | `LLM_PROVIDER` env var | `os.getenv('LLM_PROVIDER','groq')` → `PROVIDER_CONFIG` | ✓ WIRED | All three providers resolve to distinct base_url/model; unknown value raises. |
| `app/llm.py` | `app/observability.py` | `record_llm_call_attributes(span, request, response)` | ✓ WIRED | Attributes observed on a live `chat` span. |
| `app/main.py` | `app/rag.py` + `app/llm.py` | `/ask` calls `retrieve` → `build_prompt` → `generate` | ⚠️ PARTIAL | Wiring is correct, but the chain aborts at `retrieve()` in production. |
| `app/rag.py` | `app/embeddings.py` + `documents` | `embed_text` + `cosine_distance` order_by | ⚠️ PARTIAL | Correct SQL is generated (`ORDER BY documents.embedding <=> $1 LIMIT $2`) but execution fails as shipped. |
| `app/rag.py` | `app/observability.py` | `RAG_RETRIEVAL_TOP_K` / `RAG_RETRIEVAL_DOC_COUNT` | ✓ WIRED | Constants imported and set on the live span. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `app/rag.py` `retrieve()` | `docs` | `session.execute(select(Document).order_by(cosine_distance))` | **No** — raises `DataError` | ✗ DISCONNECTED (as shipped) |
| `app/rag.py` `retrieve()` (blocker removed) | `docs` | same | Yes — 3 semantically correct docs | ✓ FLOWING |
| `app/main.py` `/ask` `sources` | `docs` | `retrieve()` | Real `doc_id`/`title` on the healthy path | ✓ FLOWING (blocked upstream) |
| `app/main.py` `/ask` `answer` | `result.answer` | `llm.generate()` | Never reached in production; no live provider call ever made | ? UNVERIFIED |
| `scripts/seed_corpus.py` | `embeddings` | `embed_texts()` local model | Yes — 72 distinct unit-norm 384-d vectors in the DB | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Live corpus present and correctly typed | `psql -c "select count(*), count(distinct doc_id), count(embedding) from documents"` | `72 \| 72 \| 72` | ✓ PASS |
| Embedding dimension | `psql -c "select vector_dims(embedding), count(*) from documents group by 1"` | `384 \| 72` | ✓ PASS |
| Embeddings are real (unit-normalized, distinct) | `psql -c "select embedding <#> embedding ..."` / `count(distinct embedding::text)` | self-dot `1.0000`; `72` distinct | ✓ PASS |
| Seed script runs idempotently against live DB | `python -m scripts.seed_corpus` | `corpus seeding complete: 72 docs`; count still 72/72 | ✓ PASS |
| Real pgvector retrieval via `app/rag.py` | `retrieve(AsyncSessionLocal(), "How do I rotate an API key?")` | `DBAPIError / asyncpg.DataError` | ✗ **FAIL** |
| Same retrieval with the `register_vector` listener removed | A/B harness | `['rotate-api-key','api-key-scopes-permissions','revoke-lost-api-key']` | ✓ PASS (proves root cause) |
| `POST /ask` end-to-end against live DB | `TestClient(app).post("/ask", ...)` | **HTTP 500**, `DBAPIError` | ✗ **FAIL** |
| Production span set for a real `/ask` | In-memory exporter bound before `app.main` import | 5 spans; only `rag.retrieval` (ERROR) of the required 3 | ✗ **FAIL** |
| Span set with blocker removed | same harness | 7 spans incl. `rag.retrieval`, `rag.prompt_construction`, `chat` | ✓ PASS (achievable once fixed) |
| DB span emitted as shipped | same harness, `setup_db_instrumentation()` not called | 7 spans, **0 DB spans** | ✗ **FAIL** |
| DB span with `setup_db_instrumentation()` called | same harness, called manually | 9 spans, adds `connect` + `SELECT` | ✓ PASS (proves the fix) |
| GenAI semconv attributes on the chat span | attribute dump | `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens/output_tokens`, `agentk.llm.provider`, `agentk.llm.estimated_cost_usd` | ✓ PASS |
| Provider switch by env var | `_resolve_provider()` + `get_client()` across all values | 3 distinct base_url/model pairs; default groq; `KeyError` on unknown | ✓ PASS |
| Live provider call | — | No credential available | ? SKIP → human verification |
| Test suite | `python -m pytest tests/ -q` (run once) | `18 passed` | ✓ PASS (but see Anti-Patterns) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist and no plan or summary declares a probe. **Step 7c: SKIPPED (no probes declared or discoverable).**

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| RAG-01 | 02-01, 02-04 | `/ask` answers a support question by retrieving from pgvector and generating via the configured provider | ✗ **BLOCKED** | `POST /ask` → HTTP 500 `DBAPIError` against the live seeded DB. |
| RAG-02 | 02-01, 02-02 | 50-200 synthetic docs seeded into Postgres+pgvector via local `sentence-transformers` | ✓ SATISFIED | 72 real rows, 384-dim unit-normalized distinct vectors, no external embedding API, live seed re-run succeeded. |
| RAG-03 | 02-03, 02-04 | Every LLM call instrumented with OTel traces carrying GenAI semconv attributes | ✗ **BLOCKED** | Only 1 of 3 required spans emitted on a production request; the free DB span is never emitted; no trace confirmed in SigNoz. |
| RAG-04 | 02-03 | Single OpenAI-compatible module switching Groq/Cerebras/Gemini via env var | ? NEEDS HUMAN | Client selection proven for all 3 providers; no live call possible without a credential. |

**Orphaned requirements:** None. All four phase requirement IDs (RAG-01, RAG-02, RAG-03, RAG-04) are claimed by at least one plan's `requirements` frontmatter, and REQUIREMENTS.md maps no additional IDs to Phase 2.

**Traceability discrepancy:** `.planning/REQUIREMENTS.md` currently marks RAG-01 through RAG-04 as `[x]` / `Complete`. RAG-01 and RAG-03 are not complete per this verification and should be reopened.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `app/db.py` | 35-43 | Conflicting adapter registration (asyncpg codec + SQLAlchemy type) | 🛑 BLOCKER | Breaks every vector query; sole cause of the SC-1 failure. |
| `app/db.py` | 62-70 | Orphaned function — defined, documented, never called | 🛑 BLOCKER | D-07's free DB span never emitted. |
| `tests/conftest.py` | 94-108 | `session.execute` is an `AsyncMock` — SQL never compiled or executed | 🛑 BLOCKER | Makes the production-breaking bug undetectable by the whole suite. Confirms WR-17's substance. |
| `tests/test_ask.py` | 48 | `assert len(spans) == 3` measures a partially-bound provider | ⚠️ WARNING | Confirms WR-16. Production emits 7 spans on the healthy path; the assertion proves nothing about production. |
| `app/observability.py` | 50 | `_ESTIMATED_RATE_USD_PER_1K_TOKENS = 0.0` | ⚠️ WARNING | `agentk.llm.estimated_cost_usd` is always exactly 0.0 — Phase 5's Law 3 cost watchdog will need a real rate. Documented as intentional. |
| `app/main.py` | 55 | Synchronous `llm_module.generate(...)` called from an `async def` handler | ⚠️ WARNING | Blocks the event loop for the duration of the provider call. Matches CR-01. |
| `app/llm.py` | 144 | Unguarded `response.choices[0].message.content` | ⚠️ WARNING | A response with an empty `choices` list produces a bare 500. Matches CR-03. |
| `app/llm.py` | 90 | `api_key=os.getenv(f"{provider.upper()}_API_KEY")` passing `None` | ⚠️ WARNING | The OpenAI SDK falls back to `OPENAI_API_KEY` when `api_key` is `None`, which could transmit an unrelated key to a third-party base_url. Matches CR-04. |
| `alembic/versions/0001_create_documents.py` | 37 | Hardcoded `Vector(384)` | ⚠️ WARNING | Contradicts `app/embeddings.py`'s docstring claim that the migration derives width from `EMBEDDING_DIM`. Low practical risk (migrations are immutable by convention) but the docstring is wrong. |
| `requirements.txt` | 17-19 | `httpx`, `pytest`, `pytest-asyncio` unpinned | ⚠️ WARNING | Contradicts the project's locked-pins convention and the Day 5-6 clean-machine-rebuild gate. Matches WR-18. |
| `app/observability.py` | 6-9 | Docstring claims `app/rag.py` calls `record_llm_call_attributes` | ℹ️ INFO | It does not — `app/rag.py` sets its `rag.*` constants directly. Documentation drift only. Matches WR-11. |
| `scripts/seed_corpus.py` | 1-9 | Docstring says "upserts... keyed on doc_id"; implementation deletes all then inserts | ℹ️ INFO | Behavior is still idempotent (verified live); wording is misleading. Matches WR-09. |

**Debt-marker gate:** PASSED. No unreferenced `TBD` / `FIXME` / `XXX` markers in any file modified by this phase.

### Review-Lead Adjudication

The three review leads I was asked to reach my own verdict on:

- **CR-02 — CONFIRMED (BLOCKER).** Not merely a grep result: measured at runtime. As shipped, a healthy `/ask` emits 7 spans with zero DB spans; invoking `setup_db_instrumentation()` manually raises this to 9 spans, adding `connect` and `SELECT`. The function is genuinely orphaned.
- **WR-16 — CONFIRMED (WARNING).** Production span count for a healthy `/ask` is 7 (5 on the failing path), not 3. The `assert len(spans) == 3` passes only because `FastAPIInstrumentor` binds its tracer at import time and its 4 framework spans never reach the monkeypatched exporter. The assertion does not reflect production.
- **WR-17 — CONFIRMED IN SUBSTANCE, CORRECTED IN DETAIL.** The stated mechanism is wrong for this environment: `greenlet==3.5.4` **is** installed in `/tmp/agentk-p2`, so a real `AsyncSessionLocal().execute(...)` does not raise the greenlet error. But the conclusion is right and worse than described — the real DB path has zero coverage, and exercising it directly reveals a hard production failure (`DataError`) that all 18 mocked tests miss. This is the finding that escalates the phase from "warnings" to "goal not achieved."

Additionally, `02-04-SUMMARY.md` states that "live top_k/cosine-distance behavior was already established as working by 02-01's applied migration and 02-02's seeded corpus." That inference is false: a successful migration and a successful bulk insert do not establish that a parameterized `SELECT ... ORDER BY embedding <=> $1` executes. It does not.

### Gaps Summary

Phase 2 built a real, high-quality substrate and then never ran it. The corpus is genuine (72 varied synthetic docs, locally embedded, unit-normalized, distinct), the schema is correct, the retrieval logic is semantically excellent (asking "How do I rotate an API key?" returns `rotate-api-key`, `api-key-scopes-permissions`, `revoke-lost-api-key`), the three-span design is correct, and the provider abstraction is clean and single-sited. Every one of those is verified against live infrastructure, not claimed.

But the phase goal — "answers support questions end-to-end, with every step visible in SigNoz" — is not achieved. `POST /ask` returns HTTP 500 against the real database. One line in `app/db.py` registers the pgvector **asyncpg codec** alongside the pgvector **SQLAlchemy type**; the two serialization paths are mutually exclusive, and the combination makes every vector-bound query raise `DataError`. A second line that should have been in `app/main.py` was never written, so the D-07 "free DB span" is never emitted.

Both defects are small and localized. The A/B evidence in this report shows that removing the `register_vector` connect listener makes `/ask` return `200` with correctly grounded sources, and that calling `setup_db_instrumentation()` adds the missing `connect` and `SELECT` spans. The fix is likely under ten lines.

The reason these shipped is structural, not incidental: **every test in the phase mocks the database session**, so the pgvector SQL is never compiled or executed, and the span assertion measures a provider the framework spans never reach. 18 green tests coexist with a service that cannot serve a single request. Gap closure should add at least one integration test that executes a real query against the live container — otherwise the same class of defect will recur in Phase 3, which depends on this exact retrieval path to inject latency into.

No gaps were deferred: Phases 3-7 address failure injection, MCP, the agent loop, the policy gate, and reporting — none of them cover the pgvector adapter conflict or the DB instrumentation wiring.

---

_Verified: 2026-07-23T20:50:57Z_
_Verifier: Claude (gsd-verifier)_
