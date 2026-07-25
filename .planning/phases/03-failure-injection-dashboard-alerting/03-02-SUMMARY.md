---
phase: 03-failure-injection-dashboard-alerting
plan: 02
status: complete
requirements-completed: [FLAG-02, FLAG-04]
key-files:
  created:
    - tests/test_injection_rag.py
  modified:
    - app/rag.py
completed: 2026-07-24
---

# Phase 3 Plan 02: RAG-tier Fault Injectors (prompt-regression, retrieval-latency)

**Injected the two retrieval-tier fault scenarios into `app/rag.py`: prompt-regression (FLAG-02)
and retrieval-latency (FLAG-04). Each reads its flag fresh per call and stamps a queryable span
attribute so the symptom is visible in SigNoz — a broken prompt still returns HTTP 200, so the
`regression_active` attribute (not a status code) is the signal.**

## Accomplishments

- `app/rag.py`:
  - `BROKEN_SYSTEM_PROMPT` constant (inverts every D-05 grounding clause — ignore context, answer
    from general knowledge, never say "I don't know"), deliberately blatantly different.
  - `build_prompt`: reads `flags.is_enabled("prompt_regression")` fresh inside the
    `rag.prompt_construction` span, selects the broken prompt when ON, stamps
    `RAG_PROMPT_REGRESSION_ACTIVE` in both states. User prompt / context assembly byte-for-byte
    unchanged between branches.
  - `retrieve`: reads `flags.is_enabled("retrieval_latency")` fresh inside the `rag.retrieval` span,
    `await asyncio.sleep(RETRIEVAL_LATENCY_INJECT_S)` when ON, stamps `RAG_RETRIEVAL_LATENCY_INJECTED`
    always. Existing embed → pgvector top_k → DB-span path unchanged.
- `tests/test_injection_rag.py`: 6 tests via `in_memory_exporter` — prompt swap + attribute in both
  states, user-prompt-unchanged invariant, latency attribute + `asyncio.sleep` awaited (delay
  monkeypatched tiny so the test never sleeps real seconds).

## Verification

- `pytest tests/test_injection_rag.py -q` — 6 passed.
- Full offline suite still green (no regression to the Phase-2 `/ask` spans).
