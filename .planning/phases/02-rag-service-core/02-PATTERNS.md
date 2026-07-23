# Phase 2: RAG Service Core - Pattern Map

**Mapped:** 2026-07-23
**Files analyzed:** 7 (new/modified)
**Analogs found:** 2 exact/partial / 7 (codebase has only a Phase 1 telemetry skeleton — no prior DB/RAG/LLM code exists yet, so most new files have no in-repo analog and must follow CLAUDE.md's stack guidance directly)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `app/main.py` (modified) | route/controller | request-response | itself (existing file, extend in place) | exact |
| `app/db.py` (new) | config/provider | CRUD (async engine/session setup) | `app/telemetry.py` (provider-setup module shape) | role-match (structural only) |
| `app/rag.py` (new) | service | CRUD + transform (embed query, vector search, span emission) | `app/telemetry.py` (span/provider wiring style) + `app/main.py` (logging-inside-handler pattern) | partial |
| `app/llm.py` (new) | service | request-response (outbound HTTP to LLM provider) | none in-repo | no analog |
| `app/models.py` or `app/schemas.py` (new, Pydantic request/response) | model | transform | none in-repo | no analog |
| `app/seed.py` / `scripts/seed_corpus.py` (new, one-off loader) | utility/batch | batch, file-I/O | none in-repo | no analog |
| `alembic/` migration env + `alembic.ini` (new) | migration | batch | none in-repo | no analog |
| `requirements.txt` (modified) | config | — | itself | exact |

## Pattern Assignments

### `app/main.py` (route/controller, request-response) — MODIFY IN PLACE

**Analog:** itself, `/Users/ayushbharadva/dev/personal/Agent-K/app/main.py` (full file, 47 lines, read in one pass)

This is the file being extended, not copied from elsewhere — but its own internal ordering rules are the load-bearing pattern every new route MUST follow:

**Critical structural rule (lines 19-44):**
```python
# 1. Create the app.
app = fastapi.FastAPI()

# 2. Register routes (only /healthz in this phase - D-05).
@app.get("/healthz")
async def healthz():
    ...

# 3. Wire OTel providers (console + OTLP-HTTP dual exporters, D-06/D-07).
setup_telemetry()

# 4. Instrument the app AFTER routes are registered.
FastAPIInstrumentor.instrument_app(app)

# 5. Correlate stdlib logging records with active trace/span context.
LoggingInstrumentor().instrument(set_logging_format=True)
```

**Rule for the new `/ask` route:** it (or a router `include_router()` call) MUST be inserted at step 2, i.e. textually before `FastAPIInstrumentor.instrument_app(app)` at step 4. If `/ask` lives in a separate router module, the `include_router()` call itself must appear before step 4 — routes added after `instrument_app()` are never wrapped in spans (this is stated explicitly in the file's own docstring/comments, lines 6-8).

**Per-request logging pattern to replicate** (lines 24-34):
```python
@app.get("/healthz")
async def healthz():
    logging.getLogger(__name__).info("healthz request handled")
    return {"status": "ok"}
```
Every new route handler (`/ask`) must make an explicit `logging.getLogger(__name__).info(...)` call inside the handler body — `uvicorn.access`'s logger does not propagate to the OTel root logger, so trace-correlated logs only happen via this explicit call pattern. Apply the same call at the start of `/ask`'s handler and again for meaningful lifecycle points (e.g., "retrieval complete", "answer generated") if desired, but at minimum one call per request.

---

### `app/telemetry.py` (config/provider) — UNCHANGED, imported not modified

**Role for Phase 2:** `setup_telemetry()` is called once at startup exactly as-is. Do not re-implement or duplicate provider setup inside `app/rag.py` or `app/llm.py` — those modules obtain tracers via `opentelemetry.trace.get_tracer(__name__)` against the already-globally-registered `TracerProvider` set up here (lines 56-61 of telemetry.py: `trace.set_tracer_provider(tracer_provider)`).

**Structural pattern to mirror in `app/db.py`** (provider-setup module shape, lines 40-91):
- One `setup_x()`-style function, called once from `app/main.py`, that builds a resource/engine and registers it globally, with clear numbered-comment sections.
- `app/db.py` should follow the same shape: a `get_engine()` / `setup_db()` function that builds the async SQLAlchemy engine once (module-level singleton or FastAPI dependency), registers the pgvector type via `event.listens_for(engine.sync_engine, "connect")` per CLAUDE.md's version-compatibility note, and is called/imported from `app/main.py` in the same "wire infra, then use it" ordering style already established by `setup_telemetry()`.
- Load env vars via `load_dotenv()` + `os.getenv(...)` with a `DEFAULT_*` module-level constant fallback, exactly as `telemetry.py` does for `DEFAULT_OTLP_ENDPOINT` / `DEFAULT_SERVICE_NAME` (lines 36-37, 50-51). `app/db.py` should define `DEFAULT_DATABASE_URL` similarly and read `DATABASE_URL` from env. `app/llm.py` should define provider base-URL defaults per CLAUDE.md's locked table and read `LLM_PROVIDER` the same way.

---

### `app/rag.py` (service, CRUD+transform) — NEW, no in-repo analog for retrieval logic itself

**Analog for span-wiring style only:** `app/telemetry.py` lines 55-61 show how tracers/providers are obtained from the `opentelemetry.trace` module-level API; `app/main.py` lines 24-34 show the logging-inside-handler call convention.

**Pattern to establish (from CONTEXT.md D-06/D-07, no code precedent exists yet — this is new ground):**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def retrieve(query: str, top_k: int = 3):
    with tracer.start_as_current_span("rag.retrieval") as span:
        # embed query, run pgvector similarity search (gets free DB span
        # from opentelemetry-instrumentation-sqlalchemy underneath this span)
        span.set_attribute("rag.retrieval.top_k", top_k)
        span.set_attribute("rag.retrieval.doc_count", len(results))
        ...
```
Three spans total across the `/ask` flow (D-07): `rag.retrieval`, prompt-construction, and generation (the latter likely lives in `app/llm.py`). Each hand-written span must set custom attributes (`rag.retrieval.doc_count`, `rag.retrieval.top_k`) through the shared `record_llm_call_attributes(span, request, response)` helper referenced in D-06 — this helper does not exist yet and must be created (likely in `app/telemetry.py` or a new small `app/observability.py`), since it's explicitly meant to be reused unchanged by Phase 5's Agent K self-telemetry.

---

### `app/llm.py` (service, request-response) — NEW, no in-repo analog

No prior LLM-client code exists in this repo. Follow CLAUDE.md's locked pattern directly (not extracted from codebase):
```python
from openai import OpenAI
import os

PROVIDER_CONFIG = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.1-8b-instant"},
    "cerebras": {"base_url": "https://api.cerebras.ai/v1", "model": "..."},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "..."},
}

def get_client() -> OpenAI:
    provider = os.getenv("LLM_PROVIDER", "groq")
    cfg = PROVIDER_CONFIG[provider]
    return OpenAI(base_url=cfg["base_url"], api_key=os.getenv(f"{provider.upper()}_API_KEY"))
```
Wrap the completion call in its own `tracer.start_as_current_span("gen_ai.generation")` (or the equivalent stable `gen_ai.*` span name), and call the shared `record_llm_call_attributes(span, request, response)` helper (D-06) to set `gen_ai.*` semconv attributes — same helper as `app/rag.py` uses, single source of truth.

---

## Shared Patterns

### Provider/Infra Setup Module Shape
**Source:** `/Users/ayushbharadva/dev/personal/Agent-K/app/telemetry.py`
**Apply to:** `app/db.py`, `app/llm.py` (client factory)
```python
DEFAULT_X = "..."

def setup_x() -> None:
    load_dotenv()
    value = os.getenv("ENV_VAR", DEFAULT_X)
    ...
```

### Route Registration Ordering
**Source:** `/Users/ayushbharadva/dev/personal/Agent-K/app/main.py`, lines 19-44 (comments at lines 6-8, 40)
**Apply to:** any new route module / router include for `/ask`
Routes (or `include_router()` calls) MUST appear before `FastAPIInstrumentor.instrument_app(app)`.

### Trace-Correlated Logging
**Source:** `/Users/ayushbharadva/dev/personal/Agent-K/app/main.py`, lines 24-34
**Apply to:** every new route handler and any long-running step in `app/rag.py` / `app/llm.py`
```python
logging.getLogger(__name__).info("<lifecycle event>")
```

### Tracer Acquisition
**Source:** `/Users/ayushbharadva/dev/personal/Agent-K/app/telemetry.py`, lines 20, 56-61 (`trace.set_tracer_provider`)
**Apply to:** `app/rag.py`, `app/llm.py` — acquire tracers via `trace.get_tracer(__name__)` against the globally-registered provider; never construct a new `TracerProvider` in these modules.

### Shared GenAI Attribute Helper (must be created, not yet existing)
**Per CONTEXT.md D-06.** No source file yet — create `record_llm_call_attributes(span, request, response)` in a shared location (recommend `app/telemetry.py` or new `app/observability.py`) and import it from both `app/rag.py` and `app/llm.py`. This is explicitly designed to be reused unchanged by Agent K's Phase 5 self-telemetry, so keep its signature generic (span + request-like + response-like objects, not FastAPI/route-specific).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/llm.py` | service | request-response | No prior LLM client code in repo; follow CLAUDE.md provider table directly |
| `app/models.py`/`app/schemas.py` | model | transform | No prior Pydantic request/response models in repo (Phase 1 has no request bodies) |
| `app/seed.py` / corpus loader | utility/batch | batch, file-I/O | No prior data-seeding script exists |
| `alembic/env.py`, `alembic.ini` | migration | batch | No prior migration setup; use Alembic's standard async template (`asyncpg` engine URL) per CLAUDE.md's SQLAlchemy/asyncpg compatibility note |
| `app/db.py` | config/provider | CRUD (engine/session) | No prior DB engine code; structural shape borrowed from `app/telemetry.py` only, not a true role-match analog |

## Metadata

**Analog search scope:** `app/` directory (entire repo's application code — repo is Phase-1-only, 2 files: `app/main.py`, `app/telemetry.py`, `app/__init__.py` empty)
**Files scanned:** 3 (`app/__init__.py`, `app/main.py`, `app/telemetry.py`) + `requirements.txt`
**Pattern extraction date:** 2026-07-23
