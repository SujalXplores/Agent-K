---
phase: 02-rag-service-core
plan: 06
subsystem: observability
tags: [opentelemetry, sqlalchemy-instrumentation, fastapi, pytest]
gap_closure: true
requirements-completed: [RAG-01, RAG-03]
completed: 2026-07-24
status: complete
---

# Phase 2 Gap Closure Plan 6: Wire DB instrumentation + measure the real production span set

**`setup_db_instrumentation()` was defined but never called, so `SQLAlchemyInstrumentor` never activated and the D-07 free DB span was silently absent. Wired it into app startup, added a production span probe that binds an observable tracer provider before importing `app.main` (the only way to see FastAPI/SQLAlchemy spans, which bind their tracers at instrument time), and corrected the in-process test assertion that was passing for an accidental reason.**

## Changes

- `app/main.py`: imports and calls `setup_db_instrumentation()` from `app.db` as a new startup step, placed after `setup_telemetry()` (so the instrumentor binds to the real registered provider) and after the `/ask` route registration (preserving the routes-before-instrumentation invariant). Renumbered the trailing `LoggingInstrumentor` step.
- `scripts/probe_ask_spans.py` (new): registers an `InMemorySpanExporter`-backed `TracerProvider` as the global provider *before* importing `app.main`, stubs only the third-party LLM call (real DB, real local embedding), issues one real `POST /ask`, and writes the observed span set (names, instrumentation scopes, status, attribute *keys* only — never values) to a JSON file passed as `argv[1]`.
- `tests/test_integration_rag.py`: added `test_ask_emits_db_span_and_three_genai_spans_in_production`, which runs the probe as a subprocess and asserts on its JSON output.
- `tests/test_ask.py`: replaced the `assert len(spans) == 3` total-count assertion (which only passed because `FastAPIInstrumentor` binds its tracer at `app.main` import time, before the `in_memory_exporter` fixture monkeypatches the provider — so framework and DB spans never reached it) with an assertion scoped to `instrumentation_scope.name in ("app.rag", "app.llm")`. Added a comment and a docstring update pointing at the probe as where the real production span set is measured.

## Verification

Measured production span set for a real `POST /ask` (`scripts/probe_ask_spans.py`):
- `http_status == 200`
- 9 spans total: exactly one `rag.retrieval` (scope `app.rag`), one `rag.prompt_construction` (scope `app.rag`), one `chat` (scope `app.llm`); one `connect` + one `SELECT` (scope `opentelemetry.instrumentation.sqlalchemy` — the D-07 free DB span, previously 0); four FastAPI framework spans (scope `opentelemetry.instrumentation.fastapi`).
- `rag.retrieval` carries `rag.retrieval.top_k`/`rag.retrieval.doc_count`; `chat` carries `gen_ai.request.model`/`gen_ai.usage.input_tokens`.

Test results:
- `python -m pytest tests/test_integration_rag.py -q -m integration` → 3 passed.
- `python -m pytest tests/ -q` → 21 passed (20 + this plan's 1 new integration test; `test_ask.py`'s span assertion still passes, now for the right reason).

## Closes

SC-3 / RAG-03 (all three GenAI spans emitted on a real request) and the D-07 free-DB-span must-have — both closed by measurement, not by the existence of an instrumentation function.
