# Phase 2: RAG Service Core - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the monitored `POST /ask` endpoint on top of Phase 1's FastAPI/OTel scaffold: pgvector-backed retrieval over a seeded synthetic support-doc corpus, prompt construction, and LLM-generated answers — with retrieval, prompt-construction, and generation as three distinct GenAI-instrumented OTel spans, and the LLM provider swappable via one env var. No failure injection, dashboard, or agent logic yet — those are Phase 3+.

</domain>

<decisions>
## Implementation Decisions

**User's direction:** delegated all Phase 2 implementation decisions to Claude — "give recommendations based on the .planning folder content and that stays on track with all the phases... based on the project target take the necessary decisions and your decisions should be made by keeping hackathon in mind." The decisions below are Claude's recommendations, synthesized from PROJECT.md/REQUIREMENTS.md/ROADMAP.md/CLAUDE.md and the hackathon's judging criteria (SigNoz depth, technical excellence, UX, honesty/evidence narrative) — not re-litigated user answers.

### Support Corpus
- **D-01:** Corpus simulates support docs for a fictional B2B SaaS product (a generic project/workflow-management tool). Topics: account & billing, authentication/API keys, integrations, troubleshooting error codes, feature how-tos, security/permissions. Generic-enough domain is fast to author, has zero licensing/PII risk (matches the locked "synthetic corpus only" constraint), and gives judges an easy-to-follow demo narrative.
- **D-02:** Docs range from short FAQ-style entries (~1 paragraph) to longer troubleshooting guides (~4-5 paragraphs), 50-200 total. This length variety matters later: Phase 3's retrieval-latency and prompt-regression scenarios need visibly different retrieval/generation behavior to read convincingly in a demo, and uniform tiny docs would make the pgvector step look trivial.

### Retrieval & Chunking
- **D-03:** No chunking — each doc is embedded whole (docs are short by design per D-02). Fixed `top_k=3` retrieval, no similarity-threshold refusal branch. The prompt's grounding instruction (D-05) makes the LLM say "I don't know" when retrieved context doesn't cover the question, instead of building separate refusal logic — keeps RAG-01's pipeline minimal for a 7-day build.

### Answer Response Contract
- **D-04:** `POST /ask` returns `{"answer": str, "sources": [{"doc_id": ..., "title": ...}]}` — not answer-only. Source doc references are nearly free (retrieval already knows doc IDs) and give the demo/judges visible proof the answer is actually grounded, which also sets up a nice narrative echo with Agent K's own Law 1 evidence-first requirement in later phases.

### Prompt Template & Persona
- **D-05:** System prompt uses a plain, professional support-agent persona with an explicit grounding clause: "Answer using ONLY the provided context docs below. If the answer isn't in the docs, say you don't know." This exact clause is the deliberate regression target for Phase 3's FLAG-02 (prompt-regression scenario) — stripping/corrupting it later is what should visibly cause hallucination. Don't design the "good" prompt so cleverly that a broken variant isn't obviously different in the trace/answer.

### GenAI Instrumentation
- **D-06:** Use OTel's default/stable `gen_ai.*` semantic-convention attribute set at the pinned versions (`opentelemetry-api` 1.44.0 / `opentelemetry-instrumentation-*` 0.65b0) — do **not** opt into `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, per CLAUDE.md's explicit warning against blind mid-build opt-in. Layer custom attributes (`rag.retrieval.doc_count`, `rag.retrieval.top_k`, and an `agentk.*` prefix for anything not covered by stable semconv) through one shared `record_llm_call_attributes(span, request, response)` helper function. This helper is reused unchanged by Agent K's own Law 3 self-telemetry in Phase 5 (per CLAUDE.md's "Stack Patterns by Variant" note) — one source of truth for attribute names across both the monitored app and the agent, avoiding drift that would silently break dashboard queries built in Phase 3/7.
- **D-07:** Exactly three spans per `/ask` call — retrieval, prompt-construction, generation — satisfying RAG-03 directly. Hand-written spans layer *on top of* the free `opentelemetry-instrumentation-sqlalchemy` DB spans, not replacing them (per CLAUDE.md's "Alternatives Considered" guidance).

### LLM Provider Abstraction
- **D-08:** Env var `LLM_PROVIDER` with values `groq` | `cerebras` | `gemini`, defaulting to `groq`. A single `openai`-SDK client module swaps `base_url`/`api_key`/`model` per CLAUDE.md's locked provider table (Groq `llama-3.1-8b-instant`, Cerebras and Gemini Flash as alternates). No LiteLLM proxy — SDK-only or direct client, per CLAUDE.md's "What NOT to Use."

### Claude's Discretion
- Doc-authoring method (hand-written vs. templated/generated) — pick whichever is faster inside the 7-day window; content just needs to cover the D-01 topic areas and hit the D-02 length variety.
- Exact module layout inside `app/` beyond the Phase 1 scaffold (`app/main.py`, `app/telemetry.py`) — e.g., new `app/rag.py`, `app/llm.py`, `app/db.py` modules — whatever keeps retrieval/prompt/generation code cleanly separated for the three-span requirement (D-07).
- Embedding model: default to `sentence-transformers/all-MiniLM-L6-v2` per CLAUDE.md's primary recommendation; swap to `BAAI/bge-small-en-v1.5` only if retrieval quality looks weak in rehearsal (same API, same CPU cost, one-line change).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Technology stack, versions, and pitfalls
- `.claude/CLAUDE.md` — locked technology stack (FastAPI/SQLAlchemy/asyncpg/pgvector/sentence-transformers/OTel versions), GenAI semconv stability warning backing D-06, provider `base_url` table backing D-08, "What NOT to Use" table (LiteLLM proxy, gRPC OTLP, separate vector DB), "Stack Patterns by Variant" note backing the shared `record_llm_call_attributes` helper (D-06)

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` §"RAG Service (RAG)" — RAG-01 through RAG-04 full requirement text
- `.planning/ROADMAP.md` §"Phase 2: RAG Service Core" — goal, success criteria, dependency on Phase 1's scaffold
- `.planning/ROADMAP.md` §"Phase 3: Failure Injection..." — confirms this phase's corpus/prompt/retrieval choices (D-01, D-02, D-05) are what Phase 3's four failure scenarios will operate on and inject into
- `.planning/PROJECT.md` — zero-budget/provider/embedding constraints, synthetic-corpus-only out-of-scope note (no real/PII data)

### Prior phase context
- `.planning/phases/01-telemetry-foundation/01-CONTEXT.md` — D-04/D-05 there establish the FastAPI skeleton as a real reusable scaffold, not disposable; this phase extends it directly rather than re-wiring OTel setup

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- [app/main.py](app/main.py) — existing FastAPI `app` object with `/healthz` route; new `/ask` route(s) must be registered here (or in a router included) **before** the existing `FastAPIInstrumentor.instrument_app(app)` call at the bottom of the file, per the ordering comment already in that file.
- [app/telemetry.py](app/telemetry.py) — `setup_telemetry()` already wires dual console+OTLP exporters for traces/metrics/logs; call unchanged, don't re-implement.
- `requirements.txt` — currently pins `fastapi`, `uvicorn`, `python-dotenv`, `opentelemetry-api/sdk/exporter-otlp-http`, `opentelemetry-instrumentation-fastapi/logging`. Phase 2 needs to add: `sqlalchemy`, `asyncpg`, `pgvector`, `alembic`, `sentence-transformers`, `openai`, `opentelemetry-instrumentation-sqlalchemy`, `httpx` per CLAUDE.md's pinned versions.

### Established Patterns
- Routes-before-instrumentation ordering: anything registered after `FastAPIInstrumentor.instrument_app(app)` runs never gets wrapped in spans (documented directly in `app/main.py`'s comments).
- Trace-correlated logging requires an explicit `logging.getLogger(__name__).info(...)` call inside route handlers — `uvicorn.access`'s logger doesn't propagate to the OTel-instrumented root logger (documented in `app/main.py` and `01-CONTEXT.md`).
- OTLP exporters are imported exclusively from `opentelemetry.exporter.otlp.proto.http.*` (HTTP/protobuf, port 4318) — never the gRPC transport.

### Integration Points
- New pgvector/SQLAlchemy DB engine setup needs `opentelemetry-instrumentation-sqlalchemy` attached to the async engine (via `event.listens_for(engine.sync_engine, "connect")` per CLAUDE.md's version-compatibility note) so retrieval queries get free DB spans, with hand-written spans layered on top for `rag.retrieval.*` custom attributes (D-07).
- New `/ask` route(s) belong in `app/main.py` or a router module imported into it, following the existing route-then-instrument ordering.

</code_context>

<specifics>
## Specific Ideas

None from the user directly — they explicitly deferred all Phase 2 decisions to Claude, citing no strong opinion on RAG implementation specifics and asking for hackathon-aligned recommendations instead. The decisions in `<decisions>` above are those recommendations; treat them as the locked starting point for research/planning rather than open questions to revisit, unless something concretely doesn't work during implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. The user did not raise any new-capability ideas; they deferred implementation choices to Claude rather than proposing scope additions.

</deferred>

---

*Phase: 2-rag-service-core*
*Context gathered: 2026-07-23*
