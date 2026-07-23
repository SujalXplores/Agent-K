---
phase: 02-rag-service-core
plan: 03
subsystem: api
tags: [openai-sdk, opentelemetry, gen_ai-semconv, groq, cerebras, gemini, pytest]

# Dependency graph
requires:
  - phase: 01-telemetry-foundation
    provides: setup_telemetry() global TracerProvider registration (app/telemetry.py), tracer-acquisition convention
provides:
  - "app/observability.py: record_llm_call_attributes(span, request, response) shared GenAI-telemetry helper + RAG_RETRIEVAL_TOP_K/RAG_RETRIEVAL_DOC_COUNT attribute-name constants"
  - "app/llm.py: PROVIDER_CONFIG, get_client(), generate() - single env-var-switched OpenAI-compatible LLM client with instrumented 'chat' span"
  - "tests/conftest.py: in_memory_exporter + mock_openai_client fixtures, reusable by 02-04"
affects: [02-04-rag-endpoint, phase-05-agent-k-self-telemetry]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single shared record_llm_call_attributes(span, request, response) helper as the one source of truth for gen_ai.*/agentk.*/rag.* attribute names (D-06) - reused unchanged by Phase 5's Agent K self-telemetry"
    - "Provider factory pattern: exactly one function (get_client) constructs the openai.OpenAI client; provider selection is env-var-only (LLM_PROVIDER), never a code branch elsewhere"
    - "Per-call tracer acquisition (trace.get_tracer(__name__) inside generate(), not cached at import time) so tests can monkeypatch the global TracerProvider per-test despite OTel's set_tracer_provider being a do-once operation"
    - "Real OpenAI SDK usage.prompt_tokens/completion_tokens normalized to input_tokens/output_tokens at the generate() call site, keeping the shared helper's attribute-name shape singular"

key-files:
  created:
    - app/observability.py
    - app/llm.py
    - tests/conftest.py
    - tests/test_llm.py
  modified: []

key-decisions:
  - "gen_ai.system/agentk.llm.provider fall back to the literal string 'openai' only when no provider is supplied on the request/response objects (e.g. a bare test double); app/llm.py's generate() always supplies the real provider name (groq/cerebras/gemini) so production spans are never mislabeled"
  - "conftest.py's in_memory_exporter fixture monkeypatches opentelemetry.trace._TRACER_PROVIDER directly instead of calling trace.set_tracer_provider(), because that API is a process-wide do-once operation that silently no-ops on the second and later calls - monkeypatch gives correct per-test isolation"
  - "Estimated cost rate is 0.0 USD/1K tokens (all three locked providers are free-tier for the hackathon) - the agentk.llm.estimated_cost_usd attribute exists so the attribute name/shape is proven and ready for Phase 5 reuse, not because a real per-token cost matters yet"

patterns-established:
  - "Pattern: any future span-emitting module (app/rag.py in 02-04, Phase 5's agent state machine) imports record_llm_call_attributes and the RAG_RETRIEVAL_* / gen_ai.* / agentk.* constants from app/observability.py rather than re-typing attribute-name strings"

requirements-completed: [RAG-03, RAG-04]

coverage:
  - id: D1
    description: "Shared GenAI-telemetry helper (record_llm_call_attributes) sets stable gen_ai.* attributes + agentk.* custom attributes on a caller-supplied span, tolerating missing/None usage, never recording raw prompt/completion text or API keys"
    requirement: "RAG-03"
    verification:
      - kind: unit
        ref: "manual verify script (plan Task 1 <verify> block) — asserts gen_ai.usage.input_tokens/output_tokens, RAG_RETRIEVAL_TOP_K/DOC_COUNT constants, and None-usage tolerance"
        status: pass
      - kind: unit
        ref: "ad-hoc script confirming no span attribute contains injected secret/prompt strings (T-02-KEY)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Single OpenAI-compatible provider factory (get_client) switches Groq/Cerebras/Gemini purely via LLM_PROVIDER env var, reading api_key from the matching {PROVIDER}_API_KEY env var, rejecting unknown providers with KeyError"
    requirement: "RAG-04"
    verification:
      - kind: unit
        ref: "tests/test_llm.py#test_get_client_defaults_to_groq"
        status: pass
      - kind: unit
        ref: "tests/test_llm.py#test_get_client_switches_provider_via_env_var_only"
        status: pass
      - kind: unit
        ref: "tests/test_llm.py#test_get_client_reads_api_key_from_matching_provider_env_var"
        status: pass
      - kind: unit
        ref: "tests/test_llm.py#test_get_client_rejects_unknown_provider"
        status: pass
    human_judgment: false
  - id: D3
    description: "generate() opens exactly one 'chat' span per call carrying gen_ai.request.model + gen_ai.usage.input_tokens/output_tokens via the shared helper, and returns the assistant's answer text"
    requirement: "RAG-03"
    verification:
      - kind: unit
        ref: "tests/test_llm.py#test_generate_emits_one_chat_span_with_gen_ai_attributes"
        status: pass
      - kind: unit
        ref: "tests/test_llm.py#test_generate_returns_assistant_message_text"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-07-23
status: complete
---

# Phase 2 Plan 3: LLM Provider Abstraction + GenAI Telemetry Helper Summary

**Single env-var-switched OpenAI-compatible LLM client (Groq/Cerebras/Gemini) with an instrumented "chat" span, plus a shared `record_llm_call_attributes` helper that is the one source of truth for `gen_ai.*`/`agentk.*` attribute names across this app and Phase 5's Agent K self-telemetry.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-23T19:51:08Z
- **Completed:** 2026-07-23T19:57:00Z
- **Tasks:** 2 (Task 2 followed TDD: RED → GREEN)
- **Files modified:** 4 (all new)

## Accomplishments
- `app/observability.py`: generic, content-safe `record_llm_call_attributes(span, request, response)` helper setting stable `gen_ai.*` semconv attributes plus `agentk.llm.provider`/`agentk.llm.estimated_cost_usd`, and the `RAG_RETRIEVAL_TOP_K`/`RAG_RETRIEVAL_DOC_COUNT` constants for 02-04's retrieval span
- `app/llm.py`: `PROVIDER_CONFIG` + `get_client()` as the sole `openai.OpenAI` construction site, switched purely by `LLM_PROVIDER` (default `groq`); `generate()` wraps each completion in a single `chat` span carrying `gen_ai.*` attributes via the shared helper
- `tests/conftest.py` + `tests/test_llm.py`: 7 offline, mocked tests proving provider-switching, api-key resolution, fail-fast on unknown provider, single-span emission, and correct attribute values — zero network calls, zero real API keys

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the shared GenAI-telemetry helper and attribute-name constants** - `dae1af1` (feat)
2. **Task 2 (RED): Add failing test for LLM provider-switching + generation span** - `cfba1ac` (test)
2. **Task 2 (GREEN): Implement single OpenAI-compatible LLM client + generate()** - `1644eda` (feat)

**Plan metadata:** (this commit, created after this SUMMARY)

_TDD gate sequence confirmed in git log: test(cfba1ac) → feat(1644eda)._

## Files Created/Modified
- `app/observability.py` - Shared `record_llm_call_attributes()` helper + gen_ai/agentk/rag attribute-name constants
- `app/llm.py` - `PROVIDER_CONFIG`, `get_client()`, `generate()` — single OpenAI-compatible client + instrumented chat span
- `tests/conftest.py` - `in_memory_exporter` and `mock_openai_client` pytest fixtures (reusable by 02-04)
- `tests/test_llm.py` - 7 tests covering provider-switching, api-key resolution, fail-fast, and span/attribute assertions

## Decisions Made
- `gen_ai.system`/`agentk.llm.provider` default to the literal `"openai"` only when the caller supplies no provider on the request/response objects (bare test doubles); `app/llm.py` always supplies the real provider name, so production spans are never mislabeled — verified live: a real `generate()` call with `LLM_PROVIDER=groq` produced `gen_ai.system=groq`, not `openai`.
- `in_memory_exporter` fixture monkeypatches `opentelemetry.trace._TRACER_PROVIDER` directly rather than calling `trace.set_tracer_provider()`, because that public API is a process-wide do-once operation (verified via source inspection of `opentelemetry.trace._set_tracer_provider` / `Once.do_once`) that silently no-ops after the first real call — this would have caused every test after the first to observe the first test's exporter. `app/llm.py`'s `generate()` acquires its tracer fresh on every call (not cached at import time) specifically to make this fixture pattern work.
- `agentk.llm.estimated_cost_usd` rate is `0.0` USD/1K tokens — all three locked providers are free-tier for this hackathon — the attribute exists to prove the shape for Phase 5 reuse, not to be billing-accurate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Normalized real OpenAI SDK usage field names before calling the shared helper**
- **Found during:** Task 2 (generate() implementation)
- **Issue:** The plan's test fixture stubs `usage.input_tokens`/`usage.output_tokens` (matching the `gen_ai.*` semconv naming used by `record_llm_call_attributes`), but the real `openai==2.46.0` SDK's `CompletionUsage` object exposes `prompt_tokens`/`completion_tokens` instead (verified via `openai.types.completion_usage.CompletionUsage` source). Without a fix, production spans against a real Groq/Cerebras/Gemini response would silently get `None` for both token-count attributes even though the mocked tests would still pass.
- **Fix:** `generate()` reads `usage.input_tokens` first, falling back to `usage.prompt_tokens` (and symmetrically for output/completion), then passes a normalized `SimpleNamespace` with `input_tokens`/`output_tokens` to `record_llm_call_attributes`. `app/observability.py` itself is untouched — it still only ever reads the one canonical attribute shape.
- **Files modified:** `app/llm.py`
- **Verification:** Manual script confirmed a stub with `usage.input_tokens`/`output_tokens` still populates the span correctly (backward-compatible with the plan's test fixture); the normalization branch is a no-op fallback for that shape and only activates for real SDK responses (which expose `prompt_tokens`/`completion_tokens`, not `input_tokens`/`output_tokens`).
- **Committed in:** `1644eda` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary for production correctness — without it, real generation spans would report zero token counts once real provider traffic starts, defeating the point of RAG-03. No scope creep; mocked test behavior is unchanged.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. `GROQ_API_KEY`/`CEREBRAS_API_KEY`/`GEMINI_API_KEY` env vars are already documented in `.env.example` (added by an earlier plan) and are only needed at real-request time, not for this plan's offline tests.

## Next Phase Readiness
- `app/llm.py`'s `generate()` and `app/observability.py`'s `record_llm_call_attributes` are ready for 02-04 to import directly into the `/ask` endpoint's generation step.
- `RAG_RETRIEVAL_TOP_K`/`RAG_RETRIEVAL_DOC_COUNT` constants are ready for 02-04's retrieval span.
- `tests/conftest.py`'s `in_memory_exporter` fixture is ready for 02-04 to reuse for retrieval/prompt-construction span assertions.
- No blockers. This plan touched no files owned by 02-01 (wave-1 sibling plan currently mid-execution) or by 02-02/02-04.

---
*Phase: 02-rag-service-core*
*Completed: 2026-07-23*
