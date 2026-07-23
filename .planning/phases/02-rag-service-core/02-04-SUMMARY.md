---
phase: 02-rag-service-core
plan: 04
subsystem: api
tags: [fastapi, pgvector, sqlalchemy, opentelemetry, gen_ai-semconv, pytest]

# Dependency graph
requires:
  - phase: 02-rag-service-core (Plan 02-01)
    provides: live rag-postgres (documents table, vector(384) embedding), app/db.py (get_session, AsyncEngine + SQLAlchemyInstrumentor), app/models.py (Document), app/embeddings.py (embed_text, local-only)
  - phase: 02-rag-service-core (Plan 02-02)
    provides: seeded corpus (72 rows, non-null embeddings) for retrieve() to query against
  - phase: 02-rag-service-core (Plan 02-03)
    provides: app/llm.py (generate(), opens the "chat" span), app/observability.py (record_llm_call_attributes + RAG_RETRIEVAL_TOP_K/RAG_RETRIEVAL_DOC_COUNT constants), tests/conftest.py (in_memory_exporter, mock_openai_client)
provides:
  - "app/rag.py: retrieve() (pgvector top_k=3 cosine-distance search, opens rag.retrieval span) and build_prompt() (D-05 grounded system+user prompt, opens rag.prompt_construction span)"
  - "app/schemas.py: AskRequest/Source/AskResponse Pydantic models (D-04 {answer, sources} contract)"
  - "app/main.py: POST /ask route (registered before FastAPIInstrumentor.instrument_app(app)) wiring retrieve -> build_prompt -> generate"
  - "tests/conftest.py: stub_documents/fake_session fixtures + a TestClient `client` fixture with get_session overridden"
affects: [phase-03-failure-injection, phase-07-eval-harness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tracer acquired fresh inside each function (trace.get_tracer(__name__) inside retrieve()/build_prompt(), not cached at module import) - mirrors app/llm.py's generate() so tests/conftest.py's in_memory_exporter monkeypatch fixture observes spans opened during the test, not a stale provider captured at import time"
    - "FastAPIInstrumentor.instrument_app(app) binds its own tracer once at app.main import time (before any test's in_memory_exporter monkeypatch runs), so the outer FastAPI request span is never captured by the per-test in-memory exporter - only the three hand-opened spans (rag.retrieval, rag.prompt_construction, chat) are, which is what makes an exact `len(spans) == 3` assertion possible per /ask call in tests"
    - "app/main.py imports app.rag and app.llm as module objects (`from app import rag as rag_module`) and calls `rag_module.retrieve(...)` / `llm_module.generate(...)` rather than importing the functions directly - lets tests monkeypatch module attributes (embed_text, OpenAI) that affect the real call path exercised by the /ask route, exactly as 02-03's test_llm.py does for OpenAI"

key-files:
  created:
    - app/rag.py
    - app/schemas.py
    - tests/test_rag.py
    - tests/test_ask.py
  modified:
    - app/main.py
    - app/observability.py
    - tests/conftest.py

key-decisions:
  - "Added RAG_PROMPT_DOC_COUNT constant to app/observability.py (alongside the existing RAG_RETRIEVAL_TOP_K/RAG_RETRIEVAL_DOC_COUNT) so the rag.prompt_construction span also carries a rag.* attribute (doc_count) - keeps all rag.* attribute-name strings centralized in one file per D-06's single-source-of-truth intent, rather than defining a one-off literal directly in app/rag.py."
  - "retrieve()'s query-ordering/limit correctness is asserted against the constructed SQLAlchemy Select statement (stmt._limit_clause, stmt._order_by_clauses) rather than against mock-returned rows, since a mocked AsyncSession.execute() always returns whatever it's configured with regardless of the real statement - the offline test proves the SQL shape is correct; live top_k/cosine-distance behavior was already established as working by 02-01's applied migration and 02-02's seeded corpus."
  - "app/main.py calls `rag_module.retrieve(...)` / `llm_module.generate(...)` via imported module objects instead of `from app.rag import retrieve` - required for tests to monkeypatch `embed_text`/`OpenAI` and have the real /ask route pick up the patched attribute at call time."

patterns-established:
  - "Any future span-emitting function reused across request paths (e.g. Phase 5's agent state machine) must acquire its tracer inside the function body, not at module import time, if it needs to be exercised under tests/conftest.py's in_memory_exporter fixture."

requirements-completed: [RAG-01, RAG-03]

coverage:
  - id: D1
    description: "retrieve(session, query, top_k=3) embeds the query, runs a pgvector cosine-distance top_k search, and opens a rag.retrieval span carrying rag.retrieval.top_k/rag.retrieval.doc_count from the shared app.observability constants"
    requirement: "RAG-01"
    verification:
      - kind: unit
        ref: "tests/test_rag.py#test_retrieve_opens_span_with_top_k_and_doc_count_attributes"
        status: pass
      - kind: unit
        ref: "tests/test_rag.py#test_retrieve_honors_top_k_ordering_and_limit"
        status: pass
      - kind: unit
        ref: "tests/test_rag.py#test_retrieve_default_top_k_is_three"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_prompt(query, docs) opens a rag.prompt_construction span and returns the D-05 grounded (system, user) prompt pair, with the grounding 'say you don't know' clause present even when zero docs are retrieved (D-03 - no separate refusal branch)"
    requirement: "RAG-03"
    verification:
      - kind: unit
        ref: "tests/test_rag.py#test_build_prompt_opens_span_and_returns_grounded_system_prompt"
        status: pass
      - kind: unit
        ref: "tests/test_rag.py#test_build_prompt_with_empty_docs_still_grounds_dont_know"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /ask returns {answer, sources: [{doc_id, title}]} per the D-04 contract, wired end to end (retrieve -> build_prompt -> generate), registered before FastAPIInstrumentor.instrument_app(app)"
    requirement: "RAG-01"
    verification:
      - kind: unit
        ref: "tests/test_ask.py#test_ask_returns_answer_and_sources_matching_d04_contract"
        status: pass
      - kind: unit
        ref: "tests/test_ask.py#test_ask_sources_correspond_to_retrieved_docs"
        status: pass
      - kind: other
        ref: "python -c ordering-check comparing str.index('/ask') vs str.index('instrument_app') in app/main.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "A single POST /ask call emits exactly three GenAI-instrumented spans - rag.retrieval, rag.prompt_construction, chat - each carrying their respective rag.*/gen_ai.* attributes, asserted by count (not just presence)"
    requirement: "RAG-03"
    verification:
      - kind: unit
        ref: "tests/test_ask.py#test_ask_produces_exactly_three_genai_spans"
        status: pass
    human_judgment: false
  - id: D5
    description: "AskRequest bounds the question field (min_length=1, max_length=2000); missing/empty/oversized question returns HTTP 422 (T-02-INPUT/T-02-DoS)"
    requirement: "RAG-01"
    verification:
      - kind: unit
        ref: "tests/test_ask.py#test_ask_missing_question_returns_422"
        status: pass
      - kind: unit
        ref: "tests/test_ask.py#test_ask_empty_question_returns_422"
        status: pass
      - kind: unit
        ref: "tests/test_ask.py#test_ask_oversized_question_returns_422"
        status: pass
    human_judgment: false
  - id: D6
    description: "End-to-end human verification: real Groq-backed POST /ask returns a grounded answer, non-corpus questions get an 'I don't know' response, SigNoz trace view shows the three spans plus the free SQLAlchemy DB span, and switching LLM_PROVIDER serves via the new provider with no code change"
    verification: []
    human_judgment: true
    rationale: "Requires GROQ_API_KEY, the live seeded DB, and SigNoz UI inspection - deferred to phase's end-of-phase human_verify_mode gate per plan's <verification> section; not exercisable in an offline test run."

duration: 12min
completed: 2026-07-24
status: complete
---

# Phase 2 Plan 4: RAG Retrieval + Prompt Construction + POST /ask Endpoint Summary

**POST /ask wired end to end (pgvector top_k=3 retrieval -> D-05 grounded prompt -> LLM generation) returning `{answer, sources}`, emitting exactly three GenAI-instrumented spans per call (rag.retrieval, rag.prompt_construction, chat), proven by an offline pytest suite with zero DB/network/API-key dependency.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-07-23T20:14:00Z (approx, first Read call)
- **Completed:** 2026-07-23T20:26:02Z
- **Tasks:** 2/2
- **Files modified:** 7 (4 created: app/rag.py, app/schemas.py, tests/test_rag.py, tests/test_ask.py; 3 modified: app/main.py, app/observability.py, tests/conftest.py)

## Accomplishments

- `app/rag.py`: `retrieve(session, query, top_k=3)` embeds the query via `app.embeddings.embed_text`, runs a pgvector cosine-distance similarity search over `Document` (no chunking, no refusal branch - D-03), and opens the `rag.retrieval` span carrying `rag.retrieval.top_k`/`rag.retrieval.doc_count` via the shared `app.observability` constants. `build_prompt(query, docs)` opens the `rag.prompt_construction` span and returns the D-05 grounded (system, user) prompt pair - the grounding clause ("say you do not know") is present in the system prompt regardless of whether any docs were retrieved.
- `app/schemas.py`: `AskRequest` (question, `min_length=1`/`max_length=2000` - T-02-INPUT/T-02-DoS), `Source`, `AskResponse` - the exact D-04 `{answer, sources: [{doc_id, title}]}` contract.
- `app/main.py`: `POST /ask` registered before `FastAPIInstrumentor.instrument_app(app)` (verified via a static ordering check), wiring `rag_module.retrieve -> rag_module.build_prompt -> llm_module.generate`, logging only lifecycle markers ("ask request received"/"answer generated") - never the question/prompt/answer text (T-02-KEY).
- `tests/conftest.py` extended with `stub_documents`/`fake_session` fixtures (shared by both new test files) and a `client` TestClient fixture with `app.db.get_session` overridden.
- `tests/test_rag.py` (5 tests) and `tests/test_ask.py` (6 tests): all offline, no live DB/network/API key required. The three-span assertion in `test_ask_produces_exactly_three_genai_spans` asserts `len(spans) == 3` exactly (not just presence of each name), confirming `FastAPIInstrumentor`'s own request span does not leak into the per-test in-memory exporter (it binds its tracer once at `app.main` import time, before any test's monkeypatch runs).
- Full suite: **18/18 tests pass** (7 pre-existing `test_llm.py` + 5 `test_rag.py` + 6 `test_ask.py`), confirming no cross-plan regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build app/rag.py - retrieval span + grounded prompt-construction span** - `83dfd26` (feat)
2. **Task 2: Add AskRequest/AskResponse schemas and wire the POST /ask route (before instrument_app)** - `c30c2e4` (feat)

**Plan metadata:** (this commit, created after this SUMMARY)

## Files Created/Modified

- `app/rag.py` - `retrieve()` (rag.retrieval span) and `build_prompt()` (rag.prompt_construction span), `SYSTEM_PROMPT` (D-05)
- `app/schemas.py` - `AskRequest`, `Source`, `AskResponse` (D-04 contract)
- `app/main.py` - `POST /ask` route, registered before `instrument_app(app)`
- `app/observability.py` - added `RAG_PROMPT_DOC_COUNT` constant
- `tests/conftest.py` - `stub_documents`, `fake_session`, `client` fixtures
- `tests/test_rag.py` - 5 offline tests for `retrieve`/`build_prompt`
- `tests/test_ask.py` - 6 offline tests for `POST /ask`

## Decisions Made

- Added `RAG_PROMPT_DOC_COUNT = "rag.prompt_construction.doc_count"` to `app/observability.py` so the `rag.prompt_construction` span also carries a `rag.*` attribute, keeping every `rag.*` attribute-name string centralized in the one shared file (D-06's single-source-of-truth intent) rather than defining a one-off literal directly in `app/rag.py`.
- `retrieve()` acquires its tracer fresh inside the function body (`trace.get_tracer(__name__)` inside `retrieve()`/`build_prompt()`, not cached at module import) - required for `tests/conftest.py`'s `in_memory_exporter` monkeypatch fixture to work, mirroring the pattern 02-03 already established in `app/llm.py`'s `generate()` (a module-level cached tracer would bind to whatever provider is globally registered at `app.rag` import time and never see a later monkeypatched provider).
- `app/main.py` imports `app.rag`/`app.llm` as module objects (`from app import rag as rag_module`) rather than importing the functions directly, so tests can monkeypatch `rag_module.embed_text` / `llm_module.OpenAI` and have the real `/ask` route pick up the patched values at call time - consistent with `tests/test_llm.py`'s existing monkeypatch style.
- Query ordering/limit correctness is verified against the constructed `Select` statement's `_limit_clause`/`_order_by_clauses` (not against mock-returned rows, since a mocked `AsyncSession.execute()` always returns whatever it's configured with regardless of the actual statement) - this proves the SQL shape is correct offline; live top_k/cosine-distance behavior against the real seeded corpus is deferred to the phase's end-of-phase human verification.

## Deviations from Plan

### Auto-fixed Issues

None - both tasks executed as written, with one minor plan-supporting addition (see below) rather than a bug/blocker fix.

**1. [Rule 2 - minor addition] Added `RAG_PROMPT_DOC_COUNT` constant**
- **Found during:** Task 1 (`build_prompt` implementation)
- **Issue:** The plan calls for `rag.prompt_construction` span to exist, and Task 2's behavior spec says "the retrieval + prompt spans carry rag.* attributes" (plural), but `app/observability.py` (from 02-03) only exported `RAG_RETRIEVAL_TOP_K`/`RAG_RETRIEVAL_DOC_COUNT`, with no constant for the prompt-construction span.
- **Fix:** Added `RAG_PROMPT_DOC_COUNT = "rag.prompt_construction.doc_count"` to `app/observability.py`, set on the `rag.prompt_construction` span in `build_prompt()`.
- **Files modified:** `app/observability.py`, `app/rag.py`
- **Verification:** `tests/test_ask.py#test_ask_produces_exactly_three_genai_spans` asserts `"rag.prompt_construction.doc_count" in prompt_span.attributes`.
- **Committed in:** `83dfd26` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 minor addition, no bugs/blockers)
**Impact on plan:** Purely additive observability value consistent with D-06's centralization principle; no scope creep, no behavior change to the retrieval/prompt logic itself.

## TDD Gate Compliance

Both tasks are marked `tdd="true"` in the plan. The RED/GREEN sequence was followed procedurally for each task (test file written first, `pytest` run and confirmed failing for the correct reason - `ModuleNotFoundError`/404s - before any implementation code was written), but each task was committed as a **single `feat(...)` commit** containing both the test file and the implementation, rather than two separate `test(...)` then `feat(...)` commits. This differs from the strict RED-commit/GREEN-commit protocol used in 02-03's Task 2 (`cfba1ac` test, then `1644eda` feat). The substance of TDD (verified-failing test before implementation) was honored; only the commit granularity differs. No code-correctness impact - full suite passes 18/18.

## Issues Encountered

None.

## User Setup Required

None for the offline test suite (no DB/network/API key needed). Real end-to-end exercise of `POST /ask` (per this plan's `<verification>` end-of-phase human checks) requires `GROQ_API_KEY` in `.env` - already documented as a phase-level `user_setup` requirement in this plan's frontmatter, not newly introduced here.

## Next Phase Readiness

- `POST /ask` is fully wired and passes its offline test suite; Phase 3's failure-injection scenarios (prompt-regression targeting the D-05 grounding clause, retrieval-latency injection, etc.) can now perturb real, working retrieval/prompt/generation code paths.
- The three-span D-07 instrumentation (`rag.retrieval`, `rag.prompt_construction`, `chat`) is proven offline by span-count assertion; end-of-phase human verification (real Groq call + SigNoz trace inspection + provider-switch check) remains pending per `human_verify_mode: end-of-phase` and is the phase's final gate before Phase 3 begins.
- No blockers. This was the last plan (wave 3) of Phase 2 - Phase 2 execution is code-complete pending the end-of-phase human verification checks in this plan's `<verification>` section.

---
*Phase: 02-rag-service-core*
*Completed: 2026-07-24*

## Self-Check: PASSED

All 7 claimed files found on disk (app/rag.py, app/schemas.py, tests/test_rag.py, tests/test_ask.py, app/main.py, app/observability.py, tests/conftest.py, this SUMMARY.md). Both claimed commits (`83dfd26`, `c30c2e4`) confirmed present in `git log --oneline --all`.
