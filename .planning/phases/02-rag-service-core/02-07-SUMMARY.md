---
phase: 02-rag-service-core
plan: 07
subsystem: llm
tags: [openai-sdk, credential-handling, error-handling, pytest]
gap_closure: true
human_verification_required: true
requirements-completed: [RAG-03, RAG-04]
completed: 2026-07-24
status: complete
---

# Phase 2 Gap Closure Plan 7: Fail-fast credentials, guarded completion accessor, requirements ledger correction

**Closed two operator-approved warnings in `app/llm.py` (CR-04 credential leak, CR-03 unguarded completion accessor) and corrected `.planning/REQUIREMENTS.md`, which claimed RAG-01/RAG-03/RAG-04 complete while `02-VERIFICATION.md` recorded RAG-01/RAG-03 as failed and RAG-04 as never exercised against a live provider.**

## Changes

- `app/llm.py`:
  - `MissingProviderKeyError(RuntimeError)` — raised by new helper `_require_api_key(provider)` when `{PROVIDER}_API_KEY` is missing or an empty/whitespace string. `get_client()` now routes the credential through it instead of a bare `os.getenv(...)`, so the OpenAI SDK's own `OPENAI_API_KEY`-environment fallback can never engage and transmit an unrelated credential to a third-party `base_url`. `_resolve_provider()` still runs first, preserving the existing `KeyError`-on-unknown-provider contract.
  - `EmptyCompletionError(RuntimeError)` — raised inside `generate()`'s `chat` span (after `record_llm_call_attributes` has already run, so the failure is still attributed) when `response.choices` is empty. `message.content is None` now normalizes to `""` so `LlmResult.answer` always satisfies its `str` contract and can't produce a Pydantic serialization 500 downstream.
- `tests/test_llm.py`: 4 new tests — missing key never falls back to an ambient `OPENAI_API_KEY` sentinel (and the sentinel never appears in the error message), empty-string key is also rejected, empty `choices` raises the typed error with the `chat` span marked ERROR and still attributed, `None` content returns `""`.
- `.planning/REQUIREMENTS.md`: RAG-01 and RAG-03 checkboxes/traceability rows reopened; RAG-04 marked `Needs human verification` (a distinct state from the two plain reopens, since its provider-selection logic is proven and only the live call is unexercised). Added a "Reopened requirements" note citing `02-VERIFICATION.md` and naming `HV-1` as what closes RAG-04.

## Verification

- `python -m pytest tests/test_llm.py -q` → 11 passed (7 pre-existing + 4 new).
- Sentinel-credential probe: `OPENAI_API_KEY=sk-unrelated-sentinel` with no `GROQ_API_KEY` → `MissingProviderKeyError`, no client constructed, sentinel absent from the message.
- `app/llm.py` still has exactly one `OpenAI(` construction site (RAG-04 single-module property preserved).
- `python -m pytest tests/ -q` → 25 passed (all tests, including 3 live-DB integration tests).
- REQUIREMENTS.md ledger integrity check passed (all 50 requirement entries and all 7 phases' traceability rows intact; only RAG-01/RAG-03/RAG-04 status changed).

## Closes

CR-04 (credential-leak path) and CR-03 (opaque 500 on malformed provider response) from `02-REVIEW.md`. Requirements ledger now states only what verification backs.

## Outstanding — human verification required

These cannot be closed by any agent in this environment (no provider credential, no live SigNoz UI session available here):

- **HV-1** (closes RAG-04): set a real `GROQ_API_KEY`/`CEREBRAS_API_KEY`/`GEMINI_API_KEY` in turn via `LLM_PROVIDER`, `POST /ask`, and confirm each provider genuinely serves a grounded answer with `gen_ai.response.model` matching that provider's model family — no source edit between runs.
- **HV-2** (confirms SC-3 "in SigNoz"): run the service against the live SigNoz stack, `POST /ask` once, and confirm the trace (with all three GenAI spans + the SQLAlchemy `SELECT` span) renders in the SigNoz UI.

Both are documented in `02-07-PLAN.md`'s `<human_verification>` section. Formal re-verification of Phase 2 (setting RAG-01/RAG-03 back to `Complete`) should follow, not just these gap-closure plans landing.
