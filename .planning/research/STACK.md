# Stack Research

**Domain:** Evidence-first AI incident-response agent — FastAPI RAG service instrumented with OpenTelemetry, shipping to a Foundry-deployed SigNoz instance, investigated by a Python agent through the SigNoz MCP server.
**Researched:** 2026-07-20
**Confidence:** MEDIUM-HIGH (HIGH on package versions and GenAI semconv attribute names verified against source repos; MEDIUM on SigNoz MCP tool parameter signatures and deep-link formats where only the base pattern is officially documented; LOW/explicitly unverified on a few items called out below — see "Could Not Verify")

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 or 3.12 | Runtime for both the RAG service and the agent | FastAPI, `mcp`, and `opentelemetry-instrumentation` all target 3.9+; 3.11/3.12 give better asyncio performance and are what OTel's auto-instrumentor is tested against. Avoid 3.13 unless you verify every `opentelemetry-instrumentation-*` wheel has a 3.13 build — some contrib packages lag new Python releases. |
| FastAPI | 0.139.x (pin `>=0.139,<0.140`) | RAG support-answering service | Current PyPI latest as of 2026-07-20. Ships with Starlette/Pydantic v2; `opentelemetry-instrumentation-fastapi` instruments it via ASGI middleware with no code changes to routes. |
| Uvicorn | 0.51.x | ASGI server | Standard FastAPI companion. **Do not run with `--reload`** once `opentelemetry-instrument` wraps it — reload spawns a child process that breaks the auto-instrumentation bootstrap (confirmed in SigNoz's own Python instrumentation guide). |
| PostgreSQL | 16 (Foundry's `metastore` default) or 17 | Single datastore for support data + vector retrieval | Locked by PROJECT.md. Foundry's `metastore` molding defaults to `postgres:16` — reuse the *same* Postgres instance for the app's own tables rather than standing up a second container, since "one datastore" is a project constraint, not just a SigNoz metastore detail. Requires a manually-added `pgvector` extension (Foundry's default Postgres image does not ship pgvector — see Supporting Libraries). |
| pgvector (extension) | 0.8.5 (2026-07-08) | Vector similarity storage/search inside Postgres | Confirmed current release via pgvector's own CHANGELOG.md. `CREATE EXTENSION vector;` must run against whatever Postgres image you actually deploy — if you keep Foundry's stock `postgres:16` image it will **not** have pgvector compiled in; use `pgvector/pgvector:pg16` as the image instead (see Foundry override below). |
| OpenTelemetry Python SDK | `opentelemetry-sdk` / `opentelemetry-api` 1.44.0, `opentelemetry-distro` / `opentelemetry-instrumentation-*` 0.65b0 | Traces, metrics, logs generation | Confirmed current on PyPI as of 2026-07-20. Note the version *skew by design*: stable API/SDK packages are on the `1.x` line, all `opentelemetry-instrumentation-*` and `opentelemetry-distro` packages are still on the `0.65bN` pre-1.0 line. Pin both together — an SDK/instrumentation mismatch is the single most common OTel-Python breakage. |
| SigNoz (via Foundry) | Pin the image (`signoz/signoz:vX.Y.Z`) explicitly in `casting.yaml` | Observability backend: traces, metrics, logs, dashboards, alerts | Foundry ships a "tested, stable default version" if you omit `spec.signoz.spec.image`, but for hackathon reproducibility, pin it explicitly so a judge's clean-machine rebuild pulls the exact build you tested against, not whatever Foundry's default drifts to between your Day 1 and their Day 7 rebuild. |
| Foundry / `foundryctl` | Pin via `curl -fsSL https://signoz.io/foundry.sh \| FOUNDRY_VERSION=v0.1.4 bash` (check `github.com/SigNoz/foundry/releases` for the actual current tag at build time — do not trust v0.1.4 as current, it was the example in the docs, not verified as latest) | Deployment CLI for SigNoz + MCP server | Single CLI, single YAML, generates Docker Compose. `foundryctl cast -f casting.yaml` is the full gauge→forge→deploy pipeline; this is what gets you under the 15-minute clean-machine target. |
| SigNoz MCP server | `signoz/signoz-mcp-server:latest` deployed as a Foundry **molding** (`spec.mcp.spec.enabled: true`), not as a standalone `docker run` | Structured, tool-based query surface for the investigating agent | Foundry has first-class support for this (`docs/concepts/mcp-server.md`) — it wires `SIGNOZ_URL` to the co-located apiserver automatically, runs in HTTP mode on port 8000, and needs zero manual container wiring. This is a materially better path than the generic `docker run signoz/signoz-mcp-server` instructions in the MCP server's own README, which assume a standalone SigNoz you already have a URL for. |
| `mcp` (Python SDK) | 1.28.1 | Python client to call the SigNoz MCP server programmatically | Official `modelcontextprotocol/python-sdk`. Use `mcp.client.streamable_http.streamablehttp_client` (see code pattern below) — the SigNoz MCP server's HTTP mode is Streamable HTTP, not raw SSE, confirmed by Foundry's docs showing the client endpoint as `http://localhost:8000/mcp` and the server's own health-probe surface (`/livez`, `/readyz`) designed for a long-lived HTTP service. |
| OpenRouter | N/A (hosted API, no client library pin needed beyond `openai` SDK) | Single LLM provider for chat + embeddings | Locked by PROJECT.md. OpenAI-compatible; point the standard `openai` Python SDK at `base_url="https://openrouter.ai/api/v1"`. |
| `openai` (Python SDK) | 2.46.0 | Chat completions + embeddings client against OpenRouter | OpenRouter's own quickstart uses this SDK as a drop-in. It uses `httpx` under the hood (`httpx<1,>=0.23.0`), which matters for instrumentation (below). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opentelemetry-exporter-otlp-proto-grpc` | 1.44.0 | Ship traces/metrics/logs to SigNoz's ingester over gRPC (port 4317) | Default choice — lower overhead than HTTP/protobuf. Use `opentelemetry-exporter-otlp-proto-http` (also 1.44.0, port 4318) instead only if you hit gRPC/proxy issues in your environment; both are confirmed current and co-installable. |
| `opentelemetry-instrumentation-fastapi` | 0.65b0 | Auto-instrument FastAPI routes as spans | Zero-code via `opentelemetry-instrument uvicorn main:app`, or call `FastAPIInstrumentor.instrument_app(app)` manually if you need finer control (e.g., excluding a health-check route). |
| `opentelemetry-instrumentation-psycopg` | 0.65b0 | Auto-instrument Postgres calls as DB client spans | Use with `psycopg` (v3), not `psycopg2` — see "What NOT to Use". Captures `db.statement`, `db.system`, duration automatically; this is what gives you the DB span to intentionally slow down for the retrieval-latency incident. |
| `opentelemetry-instrumentation-httpx` | 0.65b0 | Auto-instrument outbound HTTP calls to OpenRouter | The `openai` SDK is built on `httpx`, not `requests` — instrumenting `requests` (a common copy-pasted default) will silently capture nothing for your LLM calls. Use `HTTPXClientInstrumentor().instrument()`. |
| `opentelemetry-instrumentation-logging` | 0.65b0 | Inject `trace_id`/`span_id` into stdlib `logging` records | `LoggingInstrumentor().instrument(set_logging_format=True)` (or `OTEL_PYTHON_LOG_CORRELATION=true`). Injects `otelTraceID`/`otelSpanID`/`otelServiceName` into every `LogRecord`. Pair with an OTLP log exporter (`opentelemetry.sdk._logs` + `LoggingHandler`) so structured logs — not just text — ship to SigNoz with real `trace_id` fields SigNoz can use to link logs to traces (text-embedded IDs alone don't get you the clickable link in the SigNoz UI). |
| `opentelemetry-instrumentation` / `opentelemetry-distro` | 0.65b0 | `opentelemetry-bootstrap` + `opentelemetry-instrument` CLI | SigNoz's own Python guide recommends the CLI wrapper approach (`opentelemetry-instrument uvicorn ...`) over hand-rolled SDK setup for the auto-instrumented parts; combine with manual `tracer.start_as_current_span(...)` for the agent's own investigation spans, which have no auto-instrumentor. |
| `psycopg[binary]` (psycopg 3) | 3.3.4 | Postgres driver | Async-native, matches FastAPI's async style, and is the driver `opentelemetry-instrumentation-psycopg` targets. See "What NOT to Use" for why not psycopg2. |
| `pgvector` (Python) | 0.5.0 | Vector type + distance operators for psycopg/SQLAlchemy | Thin client library (separate versioning from the Postgres extension). Register the vector type on your psycopg connection (`from pgvector.psycopg import register_vector`). |
| `mcp` client extras | 1.28.1 (same package as SDK) | Streamable HTTP transport | `from mcp.client.streamable_http import streamablehttp_client` — no separate install needed, it ships in the base `mcp` package. |
| `python-json-logger` | 4.1.0 | Structured JSON log formatting | Optional but recommended: pairs cleanly with OTLP log export and keeps your `report.md` generation and SigNoz log queries working off the same structured fields. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `foundryctl gauge` | Validate local tooling before deploy | Run before every `cast` on a fresh machine to catch a missing `docker`/`docker compose` early rather than mid-demo. |
| `foundryctl gen examples` | Generate a known-good `casting.yaml` per deployment mode | Fastest way to get a correct Docker Compose casting to start editing from, including the MCP molding block. |
| `docker compose logs -f signoz-mcp` | Debug MCP server startup | The molding publishes a health check against `/livez`; `curl -fsS localhost:8000/livez` is the fastest liveness check during development. |

## Installation

```bash
# Foundry (pin the version explicitly — verify the current tag first)
curl -fsSL https://signoz.io/foundry.sh | FOUNDRY_VERSION=<verified-current-tag> bash

# Python app + agent (single venv is fine for a hackathon-scoped monorepo)
pip install fastapi==0.139.2 "uvicorn[standard]==0.51.0" \
  "psycopg[binary]==3.3.4" pgvector==0.5.0 \
  openai==2.46.0 mcp==1.28.1 python-json-logger==4.1.0

# OpenTelemetry — pin SDK/API and instrumentation lines together
pip install opentelemetry-distro==0.65b0 \
  opentelemetry-sdk==1.44.0 opentelemetry-api==1.44.0 \
  opentelemetry-exporter-otlp-proto-grpc==1.44.0 \
  opentelemetry-instrumentation-fastapi==0.65b0 \
  opentelemetry-instrumentation-psycopg==0.65b0 \
  opentelemetry-instrumentation-httpx==0.65b0 \
  opentelemetry-instrumentation-logging==0.65b0

opentelemetry-bootstrap --action=install
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `psycopg` (v3) + `opentelemetry-instrumentation-psycopg` | `psycopg2-binary` + `opentelemetry-instrumentation-psycopg2` | Only if you have existing psycopg2-only code to reuse; psycopg2 is sync-only and fights FastAPI's async model. Both instrumentation packages exist and are both pinned to 0.65b0, so this is a real, supported alternative, not a dead end — just not the better default here. |
| `opentelemetry-exporter-otlp-proto-grpc` | `opentelemetry-exporter-otlp-proto-http` | If gRPC (port 4317) is blocked or proxied awkwardly in your environment, switch to HTTP/protobuf on port 4318 — same SDK version, just a different exporter package and endpoint. |
| Foundry MCP molding (`spec.mcp.spec.enabled: true`) | Standalone `docker run signoz/signoz-mcp-server` | Only if you are *not* using Foundry for the SigNoz deployment itself (out of scope here — Foundry is a locked constraint). |
| In-process, code-controlled artificial DB latency (`pg_sleep()` behind a feature flag) | Toxiproxy / network-level fault injection | Toxiproxy is the more "realistic" chaos-engineering tool, but it's an extra service the 7-day, no-extra-microservices constraint doesn't have room for. A flag-gated `pg_sleep(:seconds)` issued in the same query as the real pgvector search produces a genuinely slow DB span (real evidence, not a mocked delay) with zero new infrastructure. |
| Custom OTel span as a "deployment marker" | SigNoz native deployment-marker/annotation API | There is no such native API (see Could Not Verify) — this is not a preference, it's the only available option given the current product surface. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `requests` + `opentelemetry-instrumentation-requests` for OpenRouter calls | The `openai` Python SDK is built on `httpx`, not `requests`. Instrumenting `requests` will compile cleanly and silently capture zero spans for your actual LLM traffic — a very easy, very quiet bug to ship into a demo. | `opentelemetry-instrumentation-httpx` |
| `psycopg2` as the primary driver in new async FastAPI code | Sync-only; you'll either block the event loop or run it in a thread pool, adding indirection for no benefit when psycopg3 exists and is what the modern instrumentation targets. | `psycopg` (v3), `opentelemetry-instrumentation-psycopg` |
| Reading `usage`/cost fields from OpenRouter as authoritative cost for the SLO/watchdog | `:free` model variants return `cost: 0` — real, but useless for making the cost SLO, cost watchdog, and Incident 2 falsifiable (this is explicitly called out as a locked Key Decision in PROJECT.md, restated here because it's easy to "helpfully" wire up `usage.cost` directly and defeat the incident design). | Compute cost from `usage.prompt_tokens`/`usage.completion_tokens` against your own configured price table; still read `usage.*` token counts from the response (those are real and free-tier models do return them), just not `cost`. |
| A local embedding model (`sentence-transformers`, local `torch`) | Locked out by PROJECT.md — a multi-hundred-MB-to-multi-GB model download directly threatens the sub-15-minute clean-machine rebuild constraint. | OpenRouter's `/api/v1/embeddings` endpoint with `nvidia/llama-nemotron-embed-vl-1b-v2:free` (confirmed to exist in OpenRouter's embeddings catalog as of 2026-07-20). |
| GenAI semconv attribute names from memory/older blog posts (`gen_ai.system`, `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`) | These are the **pre-rename** names. The spec moved wholesale to a new repo and renamed the provider attribute and both usage-token attributes (see GenAI Semantic Conventions section below) — old tutorials and even `opentelemetry.io`'s own legacy semconv pages show the deprecated names. | `gen_ai.provider.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| Treating any `gen_ai.*` attribute as GA/stable | Every single attribute in the current registry (`registry.yaml` in `open-telemetry/semantic-conventions-genai`) is marked `stability: development` as of this research date — none are stable. | Use them anyway (they're the current, actively-maintained names — "development" means "subject to schema changes," not "don't use it"), but don't claim in your submission blog that you're conforming to a "stable" spec; say "current GenAI semantic conventions (development status)." |
| `foundryctl cast` without pinning `spec.signoz.spec.image` (and `telemetrystore.spec.image` etc.) | Foundry's stated behavior is to pin to "a tested, stable default" — but that default can change between Foundry releases. For a hackathon judged on a clean-machine rebuild days after your own, an unpinned casting risks a different SigNoz version than the one you tested against. | Pin explicit image tags for every molding you rely on in `casting.yaml`, commit both `casting.yaml` and the generated `casting.yaml.lock`. |

## GenAI Semantic Conventions (verified against source repo, 2026-07-20)

**Location moved.** `opentelemetry.io/docs/specs/semconv/gen-ai/` is now a stub pointing to a dedicated repo: `github.com/open-telemetry/semantic-conventions-genai`. The old page's own registry table shows every `gen_ai.*` attribute marked "Deprecated" — that marking means "moved," not "don't use." Verified by reading `model/gen-ai/registry.yaml` and `docs/gen-ai/gen-ai-spans.md` directly from that repo.

**Overall status: Development.** Every attribute in the current registry carries `stability: development`. Nothing in this namespace is GA. This has been true since the spec's inception and is unlikely to change before your 7-day window closes — build against current names, don't wait for stabilization.

**Attributes to actually use, per span (`gen_ai.inference.client` span type, span name `{gen_ai.operation.name} {gen_ai.request.model}`, span kind `CLIENT`):**

| Attribute | Type | Requirement | Notes |
|---|---|---|---|
| `gen_ai.operation.name` | string | Required | Values: `chat`, `generate_content`, `text_completion`, `embeddings`, `retrieval`, `create_agent`, `invoke_agent` |
| `gen_ai.provider.name` | string | Required | Values include `openai`, `anthropic`, `gcp.gemini`, `cohere`, `aws.bedrock`, etc. **This is the current name — `gen_ai.system` is the deprecated predecessor.** For OpenRouter, there is no dedicated `openrouter` provider value in the registry; use the underlying model's provider if known, or treat OpenRouter itself as the provider value (unverified which convention the ecosystem has settled on for proxy/router services — flag this as a judgment call in your instrumentation code comments). |
| `gen_ai.request.model` | string | Conditionally Required | e.g. `openai/gpt-oss-20b:free` — use the exact OpenRouter slug you configured. |
| `gen_ai.response.model` | string | — | Model that actually generated the response (can differ from requested, especially with router/fallback behavior — relevant given OpenRouter's own routing). |
| `gen_ai.usage.input_tokens` | int | — | **Current name — not `gen_ai.usage.prompt_tokens`.** Maps from OpenRouter's `usage.prompt_tokens`. |
| `gen_ai.usage.output_tokens` | int | — | **Current name — not `gen_ai.usage.completion_tokens`.** Maps from OpenRouter's `usage.completion_tokens`. |
| `gen_ai.conversation.id` | string | Conditionally Required, when available | Use for correlating a multi-turn investigation or chat session. |
| `gen_ai.request.temperature`, `.top_p`, `.max_tokens`, `.stream`, `.seed` | various | Recommended | Populate what you actually set on the request. |
| `error.type` | string | Conditionally Required if error | This one **is** stable (inherited from general semconv, not GenAI-specific). |

Agent-specific attributes worth using given PROJECT.md's investigation design: `gen_ai.agent.name`, `gen_ai.agent.id` for the investigator identity; `gen_ai.tool.name`, `gen_ai.tool.call.id` for MCP tool calls the agent makes (the MCP semconv in the same repo, `docs/gen-ai/mcp.md`, was not read in depth this pass — worth a look if you want MCP-specific span attributes beyond generic tool-call ones).

## SigNoz MCP Server — Concrete Tool Surface

Confirmed by reading the server's own README (raw GitHub) directly, not a summary of a summary:

**Transport:** HTTP mode (Streamable HTTP at `POST/GET {base}/mcp`) is what Foundry deploys (`TRANSPORT_MODE=http`, port 8000). Stdio mode also exists (spawns a local binary) but is irrelevant here since you're deploying via Foundry's Docker molding, not launching a local binary per-client.

**Auth in Foundry's default config:** Per-request header. Foundry sets `SIGNOZ_URL` on the server; it does **not** put an API key in `casting.yaml`. Each client (your Python agent, in this case) sends a `SIGNOZ-API-KEY: <key>` header per request. Mint the key from the SigNoz UI: Settings → API Keys (Admin only), at `http://localhost:8080` for the default compose deployment.

**Endpoint (Docker Compose):** `http://localhost:8000/mcp` from the host; `http://signoz-mcp:8000/mcp` from inside the compose network if your agent also runs as a compose service.

**Tool categories confirmed present (50+ tools total):**
- **Metrics:** `signoz_list_metrics`, `signoz_query_metrics`, `signoz_get_top_metrics`, `signoz_check_metric_usage`, `signoz_check_metric_cardinality`
- **Traces:** `signoz_search_traces`, `signoz_aggregate_traces`, `signoz_get_trace_details`, `signoz_list_services`, `signoz_get_service_top_operations`
- **Logs:** `signoz_search_logs`, `signoz_aggregate_logs`, `signoz_get_field_keys`, `signoz_get_field_values`
- **Alerts:** `signoz_list_alerts`, `signoz_list_alert_rules`, `signoz_get_alert`, `signoz_get_alert_history`, `signoz_create_alert`, `signoz_update_alert`, `signoz_delete_alert`
- **Dashboards:** `signoz_list_dashboards`, `signoz_get_dashboard`, `signoz_create_dashboard`, `signoz_update_dashboard`, `signoz_delete_dashboard`, `signoz_import_dashboard`, `signoz_list_dashboard_templates`
- **Views / query builder / docs:** `signoz_list_views`, `signoz_get_view`, `signoz_create_view`, `signoz_update_view`, `signoz_delete_view`, `signoz_execute_builder_query`, `signoz_search_docs`, `signoz_fetch_doc`
- **Notification channels:** list/create/update/get/delete

Pagination on list/search tools uses `hasMore` + `nextOffset`/`nextCursor` fields in responses.

**Python client connection pattern (verified against `mcp` 1.28.1 API shape via multiple current examples, not a single source — MEDIUM confidence on exact kwargs, HIGH confidence on the overall shape):**

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def query_signoz(tool_name: str, arguments: dict, api_key: str):
    headers = {"SIGNOZ-API-KEY": api_key}
    async with streamablehttp_client(
        "http://localhost:8000/mcp", headers=headers
    ) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            return result.content
```

**Not verified in this pass:** the exact JSON parameter schema (field names, required vs optional) for each individual tool — e.g., whether `signoz_search_traces` takes `start`/`end` as epoch-ms ints or ISO strings, whether filters are a query-builder JSON blob or a flat key-value map. The README documents tool *names* and categories clearly but the per-tool parameter reference lives in the server's own generated tool schemas, which are best introspected live via `session.list_tools()` against your running deployment rather than trusted from docs — **do this as a Day 1 task**, not something to hardcode from this research.

## Foundry — Concrete `casting.yaml` Mechanics

Verified by reading `docs/concepts/casting.md`, `docs/concepts/mcp-server.md`, `docs/concepts/moldings.md`, `docs/reference/casting-file.md`, `docs/reference/cli.md`, and `docs/examples/docker/compose-mcp/README.md` directly from `github.com/SigNoz/foundry`.

**Full schema shape:**
```yaml
apiVersion: v1alpha1
metadata:
  name: <deployment-name>
  annotations: {}          # only needed for systemd/ECS/Helm overrides
spec:
  deployment:
    mode: docker
    flavor: compose
  signoz:
    spec: { image: signoz/signoz:<pinned-tag> }
  ingester:
    spec: { image: <pinned-tag> }
  telemetrystore:
    spec: { image: clickhouse/clickhouse-server:<pinned-tag>, cluster: { replicas: 1, shards: 1 } }
  telemetrykeeper:
    spec: { }
  metastore:
    kind: postgres
    spec: { image: <pinned-tag or pgvector/pgvector:pg16 if reusing for app data> }
  mcp:
    spec:
      enabled: true         # disabled by default; this is the whole activation
  patches: []
```

**`foundryctl` commands (from `docs/reference/cli.md`):**
- `foundryctl gauge -f casting.yaml` — validate required tools are installed for the target mode
- `foundryctl forge -f casting.yaml -p ./pours` — generate deployment files into `./pours`; **this is the step that writes `casting.yaml.lock`**
- `foundryctl cast -f casting.yaml` — full pipeline: gauge → forge → deploy, in one step (`--no-gauge`/`--no-forge` to skip individual steps)
- `foundryctl gen examples` — scaffold a working casting file per deployment mode
- `foundryctl gen schemas` — dump the JSON Schema for `casting.yaml` (`docs/schemas/v1alpha1.yaml`)

**`casting.yaml.lock` — confirmed mechanism:** written by `forge` (and therefore also by `cast`, which runs `forge` internally). It is a **checksum/state-tracking file**, not a dependency-resolution lockfile in the npm/poetry sense — its job is to detect drift between your declared `casting.yaml` and the currently-deployed state, not to pin transitive versions. Commit it alongside `casting.yaml` as PROJECT.md requires; regenerate it any time you re-run `forge`/`cast` after editing the casting.

**MCP as a Foundry molding — this is the load-bearing finding for this research pass.** Do not follow the standalone `signoz-mcp-server` README's `docker run` instructions. Instead:
```yaml
spec:
  mcp:
    spec:
      enabled: true
```
This single flag makes Foundry generate a `signoz-mcp` compose service automatically wired to `SIGNOZ_URL=http://signoz-signoz-0:8080` (the in-network apiserver), `TRANSPORT_MODE=http`, `MCP_SERVER_PORT=8000`, published on host port 8000, with a `/livez` healthcheck — with **no API key baked into the deployment**, matching the project's own instinct that credentials shouldn't live in committed config. Confirmed with a working, hand-maintained example at `docs/examples/docker/compose-mcp/`.

**Version pinning for the 15-minute clean-machine constraint:** pin `foundryctl` itself via `FOUNDRY_VERSION=<tag>` in the install one-liner, and pin every molding's `image:` field explicitly in `casting.yaml`. Both are load-bearing for reproducibility; neither is optional if a judge's rebuild happening days after yours must produce the same stack.

## SigNoz Deep Links — Confirmed Pattern, Extrapolated Coverage

**Confirmed, current, officially documented (dated 2026-05-04 in the docs source):** the Logs Explorer deep-link format —
```
https://<signoz-host>/logs-explorer?startTime=<ms>&endTime=<ms>&panelTypes=<encoded>&compositeQuery=<double-encoded-json>
```
- `startTime`/`endTime`: epoch milliseconds, **not URL-encoded**
- `panelTypes`: `"list"`/`"graph"`/`"table"`, URL-encoded **once**
- `compositeQuery`: a JSON object (`queryType`, `builder.queryData[]`, `builder.queryFormulas`, `id`) — stringified, then URL-encoded **twice**

Full worked example with an actual `compositeQuery` JSON body is in `signoz.io/docs/logs-management/logs-api/logs-url-for-explorer-page/` — read it directly before building your link generator; the double-encoding is the detail people get wrong.

**Confirmed route for a direct trace-by-ID view:** `/trace/:id` (from the frontend's own `constants/routes.ts`, e.g. `/trace/000000000000000012345...`). A trace lookup by ID does not need a time-range window the way a search/explorer view does, so no `startTime`/`endTime` params are expected here — **not independently confirmed against a live instance in this research pass**, verify by clicking through the running SigNoz UI once and comparing the actual URL it produces.

**Extrapolated (MEDIUM confidence, not independently documented):** the Traces Explorer (`/traces-explorer`) almost certainly follows the identical `startTime`/`endTime`/`panelTypes`/`compositeQuery` pattern as Logs Explorer, since both are the same underlying query-builder UI with `dataSource: "logs"` swapped for `dataSource: "traces"` in the composite query. Dashboards (`/dashboard/:dashboardId`) likely accept `startTime`/`endTime` too, given the pattern is used app-wide. **Recommended approach for Agent K, given the under-15-minutes-and-must-actually-resolve constraint:** don't hand-build every link format from documentation alone. Click through the running SigNoz UI once per link type you need (trace, log query, dashboard panel, metric view) during Day 1, copy the real generated URL from the browser address bar, and reverse-engineer your link generator from that ground truth — then build the automated link-checker PROJECT.md requires against it. This is both faster and more reliable than trusting an extrapolation for a requirement explicitly called "load-bearing."

## SigNoz Deployment Markers — Could Not Verify a Native Feature

No dedicated deployment-marker or annotation creation API was found in official SigNoz docs, the MCP server's tool list (no `signoz_create_marker`/`signoz_create_annotation` tool exists among the 50+ tools enumerated above), or a targeted community search. SigNoz's own "Post-Deployment Monitoring with AI" use-case doc shows an AI assistant being **told** a deployment timestamp by the user in a prompt, not reading it from a stored SigNoz entity — this strongly suggests there isn't one.

**Recommendation:** implement your own deployment marker as a custom OTel span (e.g., span name `deployment.marker`, attributes `deployment.version`, `deployment.previous_version`, `deployment.timestamp`) emitted by your rollback executor at deploy/rollback time. Query it back via `signoz_search_traces` or `signoz_aggregate_traces`. This is not a workaround born of research failure — it's arguably the *better* fit for this project's "code-enforced, not convention-based" philosophy, since it makes the marker itself an auditable, evidence-linkable span like everything else Agent K produces.

## OpenRouter — Verified Endpoints, Usage Fields, and Rate Limits

**Chat completions:** `POST https://openrouter.ai/api/v1/chat/completions`, OpenAI-compatible. Standard `openai` Python SDK works as a drop-in with `base_url="https://openrouter.ai/api/v1"`.

**Embeddings:** `POST https://openrouter.ai/api/v1/embeddings`. Confirmed live via the model catalog API (`GET https://openrouter.ai/api/v1/models?output_modalities=embeddings`) — this endpoint exists and lists `nvidia/llama-nemotron-embed-vl-1b-v2:free` among 27 embedding models.

**Usage/cost fields — confirmed structure:**
```json
"usage": {
  "prompt_tokens": 123,
  "completion_tokens": 45,
  "total_tokens": 168,
  "cost": 0,
  "cost_details": { ... },
  "prompt_tokens_details": { "cached_tokens": 0 },
  "completion_tokens_details": { "reasoning_tokens": 0 }
}
```
`cost` is real and present, but is `0` for every `:free` model — this is *why* PROJECT.md locks in computing cost from a configured price table rather than reading `usage.cost` directly. Token counts (`prompt_tokens`/`completion_tokens`) are real and non-zero even on free models; map these to `gen_ai.usage.input_tokens`/`gen_ai.usage.output_tokens`.

**Free-tier rate limits — confirmed, and this is a real risk for the project's design, flagging prominently:**

| Credit history | Requests/minute | Requests/day |
|---|---|---|
| Less than $10 lifetime purchased | 20 | **50** |
| $10+ lifetime purchased | 20 | 1,000 |

A **50 requests/day** ceiling on a brand-new OpenRouter account is tight against PROJECT.md's own evaluation plan: 4 incidents × 3 runs × (however many MCP-investigation-loop LLM calls per run, plus RAG-answering calls from the seeded traffic that produces the incident in the first place, plus any scripted manual-baseline runs). It is very plausible to blow through 50/day well before finishing even a single day of dry-run testing. **Recommend:** either budget $10 of OpenRouter credit on Day 1 specifically to unlock the 1,000/day tier (cheap insurance, doesn't compromise the "free-tier models" constraint — you're paying for higher *rate limit headroom*, not for the models themselves, which stay `:free` and `$0`), or design the loop-breaker/cost-watchdog thresholds low enough that a single investigation run genuinely cannot exceed a handful of calls. Either way, do not discover this limit for the first time during the actual demo.

**Confirmed model slugs (checked against the live `/api/v1/models` catalog, 2026-07-20) — all four from PROJECT.md's Key Decisions exist and are real:**

| Slug | Context | `tools`/function-calling | `structured_outputs` | Notes |
|---|---|---|---|---|
| `google/gemma-4-26b-a4b-it:free` | 262,144 | Yes | Yes | Supports `response_format`, `structured_outputs`, `tools`, `tool_choice` — good fit for an agent needing schema-adherent output. |
| `openai/gpt-oss-20b:free` | 131,072 | Yes | Yes | Same capability profile as gemma-4 above, plus `reasoning_effort`. |
| `cohere/north-mini-code:free` | 256,000 | Yes (`tools`, `tool_choice`) | **No** | **This does not list `structured_outputs`/`response_format` in its `supported_parameters`, unlike the other three.** PROJECT.md documents this as "the fallback if agent schema adherence proves flaky" — worth flagging that it may need prompt-engineered JSON output rather than API-enforced structured output if you fall back to it, which is a materially different reliability guarantee. |
| `nvidia/llama-nemotron-embed-vl-1b-v2:free` | 131,072 | N/A (embeddings) | N/A | Multimodal (text + image) embedding model, released 2026-02-25, confirmed present in the embeddings-filtered model catalog. |

## Stack Patterns by Variant

**If you want per-LLM-call span attribution to be exact (needed for PROJECT.md's Law 3 per-call token/cost/duration instrumentation):**
- Do not rely solely on `opentelemetry-instrumentation-httpx` auto-spans for this. Wrap every OpenRouter call site in your own `with tracer.start_as_current_span(f"{operation} {model}") as span:` block, set the `gen_ai.*` attributes from the actual response object (`response.usage.prompt_tokens` etc.), and let the httpx auto-instrumentation capture the underlying HTTP span as a child. This gives you both a clean GenAI-semconv span for dashboards/MCP queries and the raw HTTP span for debugging transport issues, without duplicating work.

**If the investigation agent's MCP queries need to show up as their own spans (for Law 3's "MCP query count, query failures, repeated queries" metrics and for span-linking investigation spans back to the original incident trace):**
- Wrap each `session.call_tool(...)` call in a manual span, and use `tracer.start_span(..., links=[Link(original_incident_span_context)])` — collect the SpanContext(s) you need to link to *before* starting the span (links are set at creation time, not added after, per the OTel Python API).

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `opentelemetry-sdk==1.44.0` / `opentelemetry-api==1.44.0` | `opentelemetry-instrumentation-*==0.65b0`, `opentelemetry-distro==0.65b0` | These are the current matched pair as of 2026-07-20 — the `1.x` and `0.65bN` lines are versioned independently by design (API/SDK are stable, instrumentation packages are pre-1.0). Do not assume a newer instrumentation package number means newer/better; always match against what's actually current for both lines together. |
| `psycopg==3.3.4` | `opentelemetry-instrumentation-psycopg==0.65b0`, `pgvector==0.5.0` | psycopg3 is what both the OTel instrumentation and pgvector's Python client register against (`pgvector.psycopg`). |
| `openai==2.46.0` | `opentelemetry-instrumentation-httpx==0.65b0` | The SDK's own pinned `httpx<1,>=0.23.0` dependency is what you're actually instrumenting. |
| `mcp==1.28.1` | SigNoz MCP server (HTTP/Streamable HTTP mode) | Confirmed shape via multiple independent current examples of `streamablehttp_client`; exact per-tool argument schemas not independently verified — introspect live via `session.list_tools()`. |
| `pgvector` extension `0.8.5` | Postgres 13–18 (14+ recommended; extension dropped Postgres 12 support at 0.8.0) | If you use Foundry's default `metastore` Postgres image for your own app tables too, you must swap the image to a pgvector-enabled build (`pgvector/pgvector:pg16`) via `spec.metastore.spec.image` in `casting.yaml` — the stock Postgres image will not have the extension available. |

## Sources

- `github.com/SigNoz/signoz-mcp-server` (raw README, fetched directly) — tool list, transport modes, auth modes, Docker deployment
- `signoz.io/docs/ai/signoz-mcp-server/` — corroborating tool list and self-hosted auth config
- `github.com/SigNoz/foundry` — `docs/getting-started.md`, `docs/concepts/casting.md`, `docs/concepts/mcp-server.md`, `docs/concepts/moldings.md`, `docs/concepts/ledger.md`, `docs/reference/cli.md`, `docs/reference/casting-file.md`, `docs/examples/docker/compose-mcp/README.md`, and a shallow sparse-checkout inspection of `docs/examples/docker/compose/pours/deployment/compose.yaml` for confirmed OTLP ports (4317/4318) — all fetched as raw files directly, not AI-summarized secondhand
- `github.com/open-telemetry/semantic-conventions-genai` — `model/gen-ai/registry.yaml` and `docs/gen-ai/gen-ai-spans.md` read directly (confirmed current attribute names, stability status, span-naming convention)
- `opentelemetry.io/docs/specs/semconv/gen-ai/` and `.../registry/attributes/gen-ai/` — confirmed these pages are stubs pointing to the repo above (old attribute names shown there are explicitly deprecated)
- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) queried directly for every package version cited — `opentelemetry-{sdk,api,distro,instrumentation-*,exporter-otlp-proto-grpc}`, `fastapi`, `uvicorn`, `psycopg`, `psycopg2-binary`, `pgvector`, `mcp`, `openai`, `python-json-logger`
- `raw.githubusercontent.com/pgvector/pgvector/master/CHANGELOG.md` — current extension version and recent fix history, read directly
- `openrouter.ai/docs/api-reference/overview`, `.../limits`, `.../embeddings`, `.../quickstart` — endpoint shapes, usage/cost field structure, free-tier rate limits
- `openrouter.ai/api/v1/models` and `?output_modalities=embeddings` (live API, queried directly) — confirmed all four PROJECT.md model slugs exist, their `supported_parameters`, context lengths, and pricing
- `raw.githubusercontent.com/SigNoz/signoz/main/frontend/src/constants/routes.ts` — confirmed `/trace/:id` route directly from source
- `signoz.io/docs/logs-management/logs-api/logs-url-for-explorer-page/` (raw `.mdx` source, dated 2026-05-04) — confirmed Logs Explorer deep-link query-parameter format and encoding rules
- `signoz.io/docs/instrumentation/opentelemetry-python/` — confirmed auto-instrumentation CLI approach, env vars, warning against `uvicorn --reload`
- `signoz.io/docs/ai/use-cases/post-deployment-monitoring/` and a targeted community-forum search — basis for "no native deployment-marker API" conclusion (absence of evidence, explicitly flagged as such, not asserted as certain)

---
*Stack research for: Agent K — evidence-first AI incident-response agent on SigNoz + OpenTelemetry*
*Researched: 2026-07-20*
