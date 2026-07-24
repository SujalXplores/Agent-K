---
phase: 03-failure-injection-dashboard-alerting
plan: 01
status: complete
requirements-completed: [FLAG-01, FLAG-06]
key-files:
  created:
    - app/flags.py
    - tests/test_flags.py
  modified:
    - app/observability.py
    - app/schemas.py
    - tests/conftest.py
    - app/main.py  # admin routes; staged in the 03-04 commit (shared file)
completed: 2026-07-24
---

# Phase 3 Plan 01: Flag Foundation + Deployment Marker

**Built the in-process feature-flag store every fault injector reads (FLAG-01) and the
`deployment.marker` OTel-span emitter that distinguishes deployment-class scenarios from
non-deployment ones (FLAG-06). Owns all new `app/observability.py` fault/marker attribute
constants (D-06 single source of truth).**

## Accomplishments

- `app/flags.py`: module-level `_flags` dict (all-OFF at import), `is_enabled`/`set_flag`/`get_all`
  read fresh per call (no-restart, FLAG-01); `token_matches` uses `hmac.compare_digest` against
  `ADMIN_TOKEN` env (open when unset/empty, per D-03 local-demo decision);
  `maybe_emit_deployment_marker` emits a `deployment.marker` span **only** for
  `prompt_regression`/`retry_storm` toggled ON — the corrected FLAG-06 mechanism (SigNoz has no
  deployment-marker API; see 03-RESEARCH.md). Tracer acquired fresh via `trace.get_tracer(__name__)`.
- `app/observability.py`: appended six constants under a "fault-injection + deployment-marker"
  section (`RAG_PROMPT_REGRESSION_ACTIVE`, `RAG_RETRIEVAL_LATENCY_INJECTED`, `AGENTK_LLM_RETRY_COUNT`,
  `AGENTK_DB_POOL_EXHAUSTED`, `DEPLOYMENT_MARKER_SCENARIO`, `DEPLOYMENT_MARKER_VERSION`);
  `record_llm_call_attributes` and existing constants untouched.
- `app/schemas.py`: `FlagToggleRequest` (name/enabled, name validated against `FLAG_NAMES` via a
  **lazy** field validator to avoid an import cycle) and `FlagStateResponse`.
- `app/main.py`: `POST /admin/flags` (token-gated, emits marker) and `GET /admin/flags` (open,
  read-only audit) registered before `FastAPIInstrumentor.instrument_app` (route staged in 03-04 commit).
- `tests/conftest.py`: autouse `reset_flags` fixture (resets all flags OFF after each test).
- `tests/test_flags.py`: 14 tests — store round-trip, unknown-flag KeyError, token open/enforced,
  deployment-marker asymmetry (exactly one span for each deployment-class ON, zero otherwise),
  and endpoint 401/422/200 via TestClient.

## Verification

- `pytest tests/test_flags.py -q` — 14 passed.
- Grep: `hmac.compare_digest` present, no `==` token compare; both `/admin/flags` routes precede
  `instrument_app` in `app/main.py`.

## Notes

- FLAG-06 mechanism was corrected during planning research from "SigNoz API call" to a custom
  `deployment.marker` OTel span — SigNoz has no deployment-marker API (`signoz#6162`). Same observable
  outcome (present for scenarios 1–2, absent for 3–4). See 03-CONTEXT.md.
- The SigNoz-UI half of visualizing the marker asymmetry is human-action Plan 03-05 (HV-2 gated).
