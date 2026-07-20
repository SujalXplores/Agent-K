<!-- GSD:project-start source:PROJECT.md -->

## Project

**Agent K**

Agent K is a code-enforced incident-response agent for a FastAPI RAG support-answering service, built for the "Agents of SigNoz" hackathon (Track 01 — AI & Agent Observability, July 20–26, 2026). When a SigNoz alert fires, Agent K investigates via the SigNoz MCP server, publishes only evidence-backed root-cause claims, executes a sandboxed rollback only when a code-based policy allows it, and records its own cost/behavior as telemetry so every decision is auditable in SigNoz.

**Core Value:** Every claim Agent K publishes is backed by resolvable SigNoz evidence, and every action it takes passes a code-enforced safety gate — nothing is trust-the-model, everything is prove-it-in-telemetry.

### Constraints

- **Timeline**: Locked 7-day build window, July 20–26, 2026 — the day-by-day plan in the roadmap must map onto this exactly (see locked build plan below).
- **Budget**: Zero-budget shipped runtime — only free tiers / open-source / self-hosted. Only the Claude Code subscription (build-time tool) is paid.
- **Team skill**: No prior Docker/OTel/SigNoz experience on the team — plan must include ramp-up time, not assume fluency.
- **Team availability**: One of 4 members unavailable July 24–26 — later-phase work (Law 2/3, dashboard, eval day) has reduced capacity.
- **LLM provider**: Locked to Groq (primary) / Cerebras (overflow) / Gemini Flash (fallback) behind one OpenAI-compatible client, provider chosen via env var, optional LiteLLM routing. Embeddings are local `sentence-transformers` only.
- **Scope lock**: No additions to locked scope (section 3 of source spec) unless an existing feature is removed first — prevents hackathon scope creep.
- **Evidence integrity**: Every published claim must carry a resolvable SigNoz evidence link; a link checker run during evaluation must confirm 100% resolve.
- **Action safety**: The rollback allowlist contains exactly one action; zero actions may execute outside the Law 2 policy gate.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|------------------|
| Python | 3.11 or 3.12 | Runtime for both the RAG app and Agent K | Matches current OTel/MCP/sentence-transformers support matrices; 3.11+ gives real asyncio task-group ergonomics used by MCP's async client. Avoid 3.13 for week 1 — some instrumentation contrib packages lag newest CPython by a few weeks. **(MEDIUM)** |
| FastAPI | 0.139.2 | RAG service web framework | Current stable on PyPI (verified live, 2026-07-20). Async-native, has first-party OTel contrib instrumentation (`opentelemetry-instrumentation-fastapi`), and is what the locked spec already names. **(HIGH: version verified via PyPI API)** |
| Uvicorn | 0.51.0 | ASGI server | Standard FastAPI companion; run with `--reload` in dev, plain `uvicorn app.main:app` in the docker-compose service for prod-like demo. **(HIGH: version verified via PyPI API)** |
| PostgreSQL + pgvector extension | Postgres 16/17 image + `pgvector` extension (via `pgvector/pgvector:pg16` or `pg17` Docker image) | Single datastore for support docs + embeddings, per locked spec | One datastore instead of Postgres+separate vector DB removes an entire class of onboarding/ops surface for a zero-Docker-experience team — one container, one connection string, one thing that can break. **(MEDIUM: architecture reasoning, not version-checked — Docker image tag should be confirmed against Docker Hub at build time)** |
| `pgvector` (Python) | 0.5.0 | Python adapter registering the `vector` type with your DB driver/ORM | Released 2026-07-06 (verified via PyPI upload metadata) — current. Supports SQLAlchemy, SQLModel, Psycopg 3, asyncpg, pg8000. **(HIGH: version + release date verified via PyPI API)** |
| SQLAlchemy | 2.0.51 | ORM / query layer over Postgres | 2.0's async engine (`create_async_engine`) is the standard pairing with `asyncpg`; `opentelemetry-instrumentation-sqlalchemy` gives free DB-span instrumentation with near-zero code. **(HIGH: version verified via PyPI API)** |
| `asyncpg` | 0.31.0 | Async Postgres driver | Fastest async Postgres driver for Python; required for `postgresql+asyncpg://` SQLAlchemy URLs. **(HIGH: version verified via PyPI API)** |
| Alembic | 1.18.5 | DB migrations | Standard SQLAlchemy migration tool — use even for a hackathon so seeding scripts and schema changes are reproducible for judges re-running the build. **(HIGH: version verified via PyPI API)** |
| OpenTelemetry Python (api/sdk) | 1.44.0 | Traces, metrics, logs instrumentation core | Current stable core release (verified via PyPI). All three signals (traces/metrics/logs) ship from the same SDK version — no separate logging SDK needed. **(HIGH: version verified via PyPI API)** |
| `opentelemetry-exporter-otlp-proto-http` (or `-grpc`) | 1.44.0 | Ships spans/metrics/logs to SigNoz over OTLP | SigNoz ingests plain OTLP — no SigNoz-specific SDK exists or is needed. Prefer the HTTP/protobuf exporter over gRPC for a Docker-inexperienced team: fewer TLS/port-forwarding surprises, works over plain `http://otel-collector:4318`. **(MEDIUM: SigNoz-standard-OTLP claim is well-established but only web-search verified this session)** |
| `opentelemetry-instrumentation-fastapi` | 0.65b0 | Auto-instruments every FastAPI request as a span | One-line `FastAPIInstrumentor.instrument_app(app)` gets you request-level traces for free before writing a single manual span. Version pins to `opentelemetry-api~=1.12`, compatible with 1.44.0 core. **(HIGH: version + compat range verified via PyPI metadata)** |
| `opentelemetry-instrumentation-sqlalchemy` | 0.65b0 | Auto-instruments DB queries (including pgvector similarity searches) as spans | Retrieval-step spans (the vector search itself) come for free — critical since "retrieval step" is an explicit locked requirement needing its own visible telemetry. **(HIGH: version verified via PyPI API)** |
| `opentelemetry-instrumentation-logging` | 0.65b0 | Correlates Python `logging` records with active trace/span IDs | Gives you the "logs" leg of traces/metrics/logs for free, and log-trace correlation is what makes SigNoz's log↔trace view useful during incident investigation. **(HIGH: version verified via PyPI API)** |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | 5.6.0 | Local embeddings (no external embedding API) | Required by the locked spec's zero-budget constraint. **(HIGH: version verified via PyPI API)** |
| `sentence-transformers/all-MiniLM-L6-v2` (model) | — | Default embedding model | 384-dim, ~80MB, CPU-fast — with only 50-200 synthetic docs, index/embed time is seconds, and quality is more than adequate for a controlled demo corpus. **(LOW: web-search-only recommendation, not independently verified this session, but this model is the long-standing default "small local embedding" choice)** |
| `BAAI/bge-small-en-v1.5` (model) | — | Alternative embedding model if retrieval quality in demos feels weak | Slightly stronger retrieval quality than MiniLM at similar CPU cost; swap only if Incident 3 (retrieval latency injection) demo needs a visibly "good" baseline to regress from. **(LOW)** |
| `openai` (Python SDK) | 2.46.0 | Single OpenAI-compatible client for Groq / Cerebras / Gemini Flash | All three locked providers expose OpenAI-compatible chat-completions endpoints — one client class, swap only `base_url` + `api_key` + `model` by env var. This *is* the "single OpenAI-compatible client module" the spec calls for. **(HIGH: version verified via PyPI API; endpoint compatibility claims MEDIUM — see per-provider rows below)** |
| `litellm` (SDK only, not proxy) | 1.93.0 | Optional routing/fallback layer over the OpenAI-compatible client | Use `litellm.completion(model="groq/llama-3.1-8b-instant", ...)` as a drop-in if you want built-in retry/fallback across providers without hand-rolling it. **Use the SDK only — do NOT run LiteLLM Proxy** (see What NOT to Use). **(MEDIUM: version verified via PyPI; SDK-vs-proxy tradeoff reasoning is this agent's synthesis)** |
| `mcp` (official MCP Python SDK) | 1.28.1 | Agent K's client to the SigNoz MCP server | This *is* the official SDK named in the locked spec. Client pattern: `stdio_client(StdioServerParameters(command="./signoz-mcp-server", env={"SIGNOZ_URL":..., "SIGNOZ_API_KEY":...}))` + `ClientSession` + `session.call_tool(name, args)`. **(MEDIUM: version verified live via PyPI; import-path pattern cross-checked against official quickstart repo but not independently executed this session)** |
| `pydantic` | 2.13.4 | Structured claim schema (Law 1: claim/confidence/evidence[]), config models, API request/response models | Already a FastAPI dependency; use it for the evidence-schema validation that Law 1 depends on — a claim that fails schema validation is easy to strip before it reaches the report renderer. **(HIGH: version verified via PyPI API)** |
| `httpx` | latest (pulled in by `openai`/FastAPI TestClient) | HTTP calls from Agent K to the RAG app's admin/feature-flag endpoint, and to the incident-report FastAPI service | Async-native, already a transitive dependency of the OpenAI SDK — no need to add `requests`. **(MEDIUM)** |
| `python-dotenv` | latest | Loads `.env` for provider API keys / SigNoz URL locally | Standard for keeping the "one env var switches provider" requirement out of shell exports during a chaotic 7-day build. **(MEDIUM)** |
| `tenacity` | latest | Retry logic for MCP calls / LLM calls | Optional — only add if the retry-storm failure scenario needs a real retry implementation to inject faults into (rather than hand-rolling retry loops in the state machine, which may be preferable for full Law-3 visibility of each retry as a span). **(LOW — architectural judgment call, flag for phase-specific research)** |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker Desktop / Docker Engine + Compose v2 | Runs SigNoz (via Foundry-generated compose), the RAG app, and Postgres | This is the team's biggest onboarding risk (zero prior Docker experience) — see Pitfalls. Install and smoke-test (`docker compose version`) on every teammate's machine on Day 1, before any code is written. |
| `foundryctl` (SigNoz Foundry CLI) | Declarative, reproducible SigNoz install | Install via `curl -fsSL https://signoz.io/foundry.sh \| bash`. Workflow: `foundryctl gauge -f casting.yaml` (validate prereqs) → `foundryctl forge -f casting.yaml` (generates compose files + `casting.yaml.lock`) → `foundryctl cast -f casting.yaml` (full pipeline, runs `docker compose up -d`). This satisfies the locked "Foundry deployment, casting.yaml + casting.yaml.lock committed" requirement directly — `casting.yaml.lock` is auto-generated by `forge`, not hand-written. **(MEDIUM: web-search verified only)** |
| `ruff` | Lint + format | Single fast tool replaces flake8+black+isort — one less thing to configure in a 7-day window. |
| `pytest` + `pytest-asyncio` | Tests for retrieval, policy gate (Law 2), evidence-schema validation (Law 1) | Prioritize testing the Law 1/2/3 enforcement code paths — these are the judged "code-enforced" claims and are cheap to unit test in isolation from the LLM. |
| SigNoz UI (self-hosted, via Foundry) | Dashboards, alerts, MCP server config, trace/log/metric explorer | Hand-build dashboards/alerts here per locked decision — do not reach for dashboard-as-code even though it exists, it's explicitly out of scope. |

## Installation

# Core RAG service

# OpenTelemetry (traces + metrics + logs + OTLP export + FastAPI/SQLAlchemy/logging auto-instrumentation)

# LLM client + embeddings

# optional:

# Agent K process (separate from the RAG app; can share a venv for hackathon speed)

# Dev tooling

# SigNoz install (run once, from repo root — generates casting.yaml.lock)

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|--------------|-------------|--------------------------|
| Single `openai` SDK with swappable `base_url`/`api_key`/`model` per provider | LiteLLM Proxy (separate gateway service) | Use the proxy only if you specifically need automatic multi-provider fallback/cooldown *and* have Docker headroom for one more service — not recommended for this team's 7-day, zero-Docker-experience constraint. |
| `pgvector` Python adapter directly on SQLAlchemy/asyncpg | A dedicated vector DB (Qdrant, Weaviate, Chroma) | Only if corpus size or query patterns outgrow Postgres — irrelevant at 50-200 docs; adding a second datastore would also violate the locked "single datastore" decision. |
| `opentelemetry-instrumentation-sqlalchemy` auto-instrumentation for the retrieval step | Hand-written spans wrapping the retrieval function | Add hand-written spans *in addition to* auto-instrumentation only where you need custom attributes (e.g., `rag.retrieval.doc_count`, `rag.retrieval.top_k`) that auto-instrumentation can't know about — don't replace the free DB spans, layer on top of them. |
| `all-MiniLM-L6-v2` embedding model | `BAAI/bge-small-en-v1.5` | Swap if retrieval-quality demos look weak in rehearsal — both are small enough for CPU-only Docker containers. |
| Manual `gen_ai.*` span attributes set in your own client wrapper | `opentelemetry-instrumentation-openai` (community auto-instrumentation, v0.62.1 on PyPI) | Auto-instrumentation is faster to wire up but gives less control over exactly which custom attributes (cost estimate, provider name, investigation-loop iteration) get attached — given Law 3 requires very specific self-telemetry (token counts, estimated cost, MCP query counts), hand-rolling the span attributes around each LLM call gives more precision. If time is short, use the auto-instrumentation package as a fallback and layer custom attributes on top via `span.set_attribute()` inside the same call. |
| Foundry (`foundryctl cast`) | Legacy `install.sh` | `install.sh` is being deprecated in favor of `foundryctl` (per SigNoz repo issue tracker) — and the locked spec explicitly requires `casting.yaml`/`casting.yaml.lock`, which only Foundry produces. Don't use the legacy installer. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| LiteLLM **Proxy** (standalone gateway container) | Adds a fourth Docker service (RAG app, Postgres, SigNoz stack, LiteLLM proxy) for a team with zero prior Docker experience — more compose networking, more ports, more things that silently fail during the SigNoz-install ramp-up days. Its automatic `gen_ai.*` OTel v2 tracing only activates in proxy mode (`LITELLM_OTEL_V2=true`), which is exactly the mode you're avoiding. | LiteLLM **SDK** (`litellm.completion(...)`) called in-process from the same client module as the `openai` SDK, or skip LiteLLM entirely and just swap `base_url` on the `openai` client. |
| gRPC OTLP exporter as the default | gRPC adds TLS/HTTP2 and port (4317) considerations that are one more thing to debug blind during Docker-compose networking setup; HTTP/protobuf (port 4318) is more forgiving to curl/test manually when something isn't showing up in SigNoz. | `opentelemetry-exporter-otlp-proto-http`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` |
| A separate vector database (Qdrant/Weaviate/Pinecone/Chroma) | Explicitly against the locked "single datastore" decision, and it's one more container/API surface with its own auth/networking to learn under time pressure. | `pgvector` extension inside the same Postgres container already running for support data. |
| An agent framework (LangGraph, PydanticAI, CrewAI, AutoGen) | Explicitly out of scope per locked decision — the team wants full code-level control over Law 1/2/3 enforcement, and none of these frameworks make policy-gate enforcement easier; they make it harder to prove "code-enforced, not trust-the-model" to judges. | Plain Python state machine (a small `enum`-driven loop with explicit transition functions) — this is also what the locked spec names directly. |
| Legacy `install.sh` for SigNoz | Being deprecated by SigNoz in favor of Foundry, and doesn't produce `casting.yaml`/`casting.yaml.lock`, which are mandatory judged deliverables. | `foundryctl cast -f casting.yaml` |
| Provider-specific SDKs (`groq`, `cerebras-cloud-sdk`, `google-genai`) as the primary client | Each has slightly different method signatures — using three different SDKs defeats the purpose of "one OpenAI-compatible client module, provider chosen via env var." | The `openai` Python SDK pointed at each provider's OpenAI-compatible `base_url` (Groq: `https://api.groq.com/openai/v1`; Cerebras: `https://api.cerebras.ai/v1`; Gemini: `https://generativelanguage.googleapis.com/v1beta/openai/`). |
| Auto-injecting `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` without reading current attribute names first | GenAI semantic conventions are still in Development status and attribute names have shifted release to release; blindly opting into "latest experimental" mid-build risks your dashboard queries breaking if you upgrade an OTel package. | Pick one attribute set at project start (either default/stable or the experimental opt-in), document it, and don't change it mid-build. Recheck the [OpenTelemetry GenAI semconv registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) at build start for exact current attribute names before writing the instrumentation wrapper. |

## Stack Patterns by Variant

- Fall back to SigNoz's plain `docker-compose.yaml` from the `SigNoz/signoz` repo (non-Foundry path) to unblock instrumentation work, then retrofit `casting.yaml`/`.lock` once things are stable — Foundry reproducibility is a judged deliverable but shouldn't block the whole team's ramp-up if it's fighting you.
- Because: judging criteria weigh 6 categories roughly equally; a working demo with retrofitted Foundry config beats a broken demo with a "correct" install path.
- Use `BAAI/bge-small-en-v1.5` instead, same `sentence-transformers` API, same CPU cost profile.
- Because: swapping models is a one-line change (`SentenceTransformer("BAAI/bge-small-en-v1.5")`), no architecture impact.
- Wrap all `gen_ai.*` attribute-setting in one shared helper function (`record_llm_call_attributes(span, request, response)`) used by both the RAG app's answer-generation step and Agent K's own LLM calls (for Law 3 self-telemetry).
- Because: this is the only "custom" instrumentation code doing double duty for both the app being monitored and the agent's self-observability — a single source of truth avoids attribute-name drift between the two, which would silently break dashboard queries that expect the same schema everywhere.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `opentelemetry-api==1.44.0` | `opentelemetry-instrumentation-fastapi==0.65b0` | Contrib package declares `opentelemetry-api~=1.12`, satisfied by 1.44.0. Keep all `opentelemetry-instrumentation-*` and `opentelemetry-exporter-*` packages pinned to the same `0.65b0` line as each other; mixing contrib versions is a common source of import errors. |
| `sqlalchemy==2.0.51` | `asyncpg==0.31.0`, `pgvector==0.5.0` | Use `postgresql+asyncpg://` connection URL; for async engines, register the vector type via `event.listens_for(engine.sync_engine, "connect")` calling `register_vector_async` (asyncpg needs explicit registration unlike psycopg2's auto-adapter). |
| `openai==2.46.0` (Python SDK) | Groq / Cerebras / Gemini OpenAI-compat endpoints | All three support Chat Completions via the SDK's `base_url` override. Gemini's compat layer supports only Chat Completions + Embeddings — don't rely on Gemini-compat mode for anything beyond that (no native tool-calling parity guarantees; test this early since Gemini Flash is your tool-calling fallback provider per the locked spec). |
| `mcp==1.28.1` (Python SDK) | SigNoz MCP server (Go binary, any recent release) | MCP protocol version compatibility is handled by the `initialize()` handshake in `ClientSession` — no manual version pinning needed between the Python SDK and the Go server binary. |

## Sources

- PyPI JSON API (`pypi.org/pypi/<package>/json`) — direct live version checks for fastapi, uvicorn, pydantic, sqlalchemy, asyncpg, psycopg, pgvector, sentence-transformers, opentelemetry-api/sdk/exporter-otlp/instrumentation-{fastapi,sqlalchemy,logging,httpx,openai}, opentelemetry-distro, litellm, mcp, openai, groq, google-genai, alembic, openinference-instrumentation-openai. **(HIGH confidence — authoritative registry, checked 2026-07-20)**
- [SigNoz MCP Server — AI Assistant Integration Guide](https://signoz.io/docs/ai/signoz-mcp-server/) — install/transport modes, env vars, tool list **(MEDIUM)**
- [github.com/SigNoz/signoz-mcp-server](https://github.com/SigNoz/signoz-mcp-server) — install methods, config **(MEDIUM)**
- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk) — official client API pattern **(MEDIUM)**
- [github.com/SigNoz/foundry](https://github.com/SigNoz/foundry) — foundryctl commands, casting.yaml.lock generation **(MEDIUM)**
- [SigNoz — Introducing Foundry](https://signoz.io/blog/introducing-signoz-foundry/) — Foundry install curl script **(LOW — single source, not cross-checked)**
- [OpenTelemetry — Gen AI semantic conventions registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — attribute names, stability status **(LOW — page redirect encountered, relied on secondary web-search summary; re-verify exact attribute names at build start)**
- [SigNoz — Implementing OpenTelemetry in FastAPI](https://signoz.io/blog/opentelemetry-fastapi/) — FastAPI + OTLP setup pattern **(LOW)**
- [Groq — OpenAI Compatibility docs](https://console.groq.com/docs/openai) — base_url, unsupported fields **(LOW)**
- [Cerebras — OpenAI Compatibility docs](https://inference-docs.cerebras.ai/resources/openai) — base_url, extra_body note **(LOW)**
- [Google AI — Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) — base_url, supported API surface **(LOW)**
- [LiteLLM — OpenTelemetry v2 docs](https://docs.litellm.ai/docs/observability/opentelemetry_v2) — proxy-only OTel v2 tracing behavior **(LOW)**
- [LiteLLM — Providers docs](https://docs.litellm.ai/docs/providers) — SDK usage pattern **(LOW)**

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
