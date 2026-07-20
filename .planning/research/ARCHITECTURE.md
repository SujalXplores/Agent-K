# Architecture Research

**Domain:** Evidence-first, safety-gated, self-observing incident-response agent (single-tenant, hackathon scope)
**Researched:** 2026-07-20
**Confidence:** MEDIUM-HIGH (component boundaries and safety pattern: HIGH, confirmed against official Docker/OTel/SigNoz docs; exact SigNoz webhook payload shape and Foundry extension syntax: MEDIUM, docs are sparse/new and were only partially retrievable)

This document assumes the LOCKED decisions in `.planning/PROJECT.md`: explicit Python state machine (no agent framework), deployer sidecar owns Docker control, single Postgres for both app data and pgvector, OpenRouter as sole LLM/embeddings provider, Foundry/`casting.yaml` for SigNoz deployment. It does not re-litigate those decisions — it researches how to structure the system *within* them.

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL                                                                  │
│  OpenRouter (chat + embeddings, HTTPS)                                    │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     │ used by both, independently
        ┌────────────────────────────┴───────────────────────────┐
        ▼                                                          ▼
┌───────────────────┐                                    ┌───────────────────┐
│  app (FastAPI RAG) │──OTLP──▶┌───────────────────┐◀──OTLP──│  agent-k          │
│  service.name=     │         │ SigNoz stack       │         │ service.name=      │
│  rag-support-app   │         │ (via Foundry)      │         │ agent-k            │
│                     │         │ - otel-collector   │         │                    │
│  reads/writes  ────▶│         │ - clickhouse       │         │ - webhook receiver │
└─────────┬───────────┘         │ - query-service    │         │ - state machine    │
          │                     │ - frontend (UI)     │◀──────▶│ - policy gate      │
          ▼                     │ - alertmanager      │  MCP   │                    │
┌───────────────────┐           └─────────┬──────────┘  (query)└──────┬─────┬───────┘
│ postgres+pgvector  │                     │ webhook (alert fires)      │     │
│ (app data + RAG    │                     └────────────────────────────┘     │
│  vector index)     │                                                        │
└───────────────────┘                                     rollback (1 route,  │
                                                            authenticated) ────┘
                                                                                │
                                                                                ▼
                                                                    ┌───────────────────┐
                                                                    │  deployer sidecar  │
                                                                    │  (owns docker.sock)│
                                                                    │  POST /rollback    │
                                                                    │  GET  /health      │
                                                                    └─────────┬──────────┘
                                                                              │ docker compose
                                                                              ▼
                                                                    (recreates `app` service
                                                                     with pinned prior image tag)
```

**Sandbox boundary:** the only component with Docker socket access is `deployer`. `agent-k` has no host mounts, no socket, no shell-out to `docker`. That is Law 2's "sandbox" check made structural rather than conventional — a compromised or misbehaving `agent-k` process physically cannot touch anything but its one authenticated HTTP call to `deployer`.

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `app` (FastAPI RAG) | Answers support questions using retrieval over Postgres+pgvector, calls OpenRouter for chat + embeddings, emits OTLP traces/metrics/logs with GenAI semantic-convention attributes. Has no knowledge that it is being investigated or may be rolled back. | The "patient." Owns its own DB connection; nothing else touches Postgres directly. |
| `postgres` (pgvector) | Single datastore for support tickets/KB content and the vector index used for retrieval. | Only `app` (and a seed script) connects to it. Agent K never queries Postgres directly — it only sees the app through telemetry, which is the honest version of "the agent investigates like a human would." |
| SigNoz stack (Foundry-managed: otel-collector, clickhouse, query-service, frontend, alertmanager) | Ingests OTLP from both `app` and `agent-k`, stores it, serves queries, evaluates alert rules, fires webhooks, serves the dashboard UI to humans. | Deployed and versioned as a unit by `foundryctl`/`casting.yaml`; do not hand-edit its compose files — extend via Foundry's molding mechanism or a separate compose file joined on the same Docker network. |
| SigNoz MCP server | Exposes SigNoz's query API (metrics, traces, logs, alerts, dashboards, services) over MCP to `agent-k`. Authenticates to SigNoz via an API key; SigNoz-side, not Agent-K-side. | This is Agent K's *only* path to evidence. It is read/query-oriented for investigation purposes even though the tool surface technically supports dashboard/alert mutation — Agent K's code should only ever call the query/search/aggregate/get tools, never the create/update/delete tools, and that restriction should be enforced in Agent K's MCP client wrapper, not assumed from the tool's own permissions. |
| `agent-k` | The state machine: receives alert webhooks, runs collect → hypothesize → validate → policy gate → act → verify → report, emits its own OTel telemetry, calls OpenRouter for reasoning, calls the deployer's single endpoint when the policy gate authorizes it. | Owns every LLM call site (by Key Decision) — this is also the natural place to own every MCP call site, which is what makes the loop-breaker and cost watchdog possible without instrumenting a third-party framework. |
| `deployer` sidecar | The only component holding the Docker socket. Exposes exactly one mutating action: rollback the `app` service to its previously known-good image tag. Everything else (arbitrary compose commands, exec, image builds) is unreachable from its API surface. | Safety-critical. Treat its own code, not Docker socket permissions, as the primary safety mechanism (see Deployer Sidecar Pattern below). |

## Recommended Project Structure

```
agent-k/                          # monorepo root
├── casting.yaml                  # Foundry: describes the SigNoz deployment
├── casting.yaml.lock             # Foundry: pinned/reproducible version lock
├── docker-compose.yml            # app + postgres + agent-k + deployer, joined onto
│                                  # the Docker network Foundry's compose creates
│                                  # (or a docker-compose.override.yml layered on top
│                                  # of Foundry's generated pours/ output — see
│                                  # "Integration Points" for which approach to pick)
├── app/                          # the monitored FastAPI RAG service
│   ├── main.py
│   ├── rag/                      # retrieval + generation pipeline
│   ├── otel/                     # OTel SDK setup, GenAI attribute helpers
│   ├── flags/                    # seeded-incident toggles (env or config-driven)
│   └── db/                       # Postgres + pgvector schema, seed scripts
├── agent/                        # Agent K itself
│   ├── main.py                   # FastAPI app: /webhook/alert, /health, /demo/trigger
│   ├── pipeline/
│   │   ├── state.py              # accumulating InvestigationState (Pydantic)
│   │   ├── collect.py            # stage: fixed MCP query set → evidence
│   │   ├── hypothesize.py        # stage: LLM call → RCA claim(s)
│   │   ├── validate.py           # stage: Law 1 — strip unsupported claims
│   │   ├── policy_gate.py        # stage: Law 2 — six-check gate, pure function
│   │   ├── act.py                # stage: call deployer /rollback
│   │   ├── verify.py             # stage: post-action MCP query
│   │   └── report.py             # stage: render Markdown + summary span
│   ├── schema/                   # Pydantic models: Claim, Evidence, PolicyVerdict...
│   ├── mcp_client.py             # thin wrapper restricting tool calls to read-only set
│   ├── llm.py                    # single OpenRouter call site (chat + embeddings)
│   ├── cost.py                   # shared price-table lookup (see Build Order risk #1)
│   ├── otel/                     # Agent K's own instrumentation, distinct service.name
│   └── watchdog/                 # loop breaker, cost watchdog
├── deployer/                     # the sidecar — kept intentionally tiny
│   ├── main.py                   # POST /rollback, GET /health — nothing else
│   ├── auth.py                   # shared-secret / bearer-token check
│   └── docker_ops.py             # the only code in the repo that shells to docker/compose
├── infra/
│   ├── dashboards/                # SigNoz dashboard JSON (service health, incident
│   │                               # context, agent health, action audit trail)
│   ├── alerts/                    # SigNoz alert rule definitions (as code/JSON,
│   │                               # applied via SigNoz API or MCP admin tools)
│   └── seed-incidents/            # config for the 4 toggleable incidents
├── eval/                          # harness: 4 incidents × 3 runs, accuracy/cost/time
└── docs/ + blog/                  # submission material
```

### Structure Rationale

- **`agent/pipeline/` mirrors the locked stage list exactly**, one file per stage. This is what "each stage is independently testable and independently instrumented" means concretely — each file exports a pure(ish) function `def run(state: InvestigationState) -> InvestigationState`, unit-testable with a fixture `InvestigationState` and no network calls except the one the stage owns.
- **`deployer/` is deliberately small and dependency-light.** It should not import Agent K's code or vice versa. The only contract between them is an HTTP request/response schema. This is what makes the sandbox boundary real rather than aspirational — if `deployer` imported `agent/`, a bug in Agent K's dependency tree could reach the Docker socket transitively.
- **`agent/cost.py` is shared** by the app's own cost computation needs (Day 2 SLO) and Agent K's own cost watchdog (Day 6) — see Build Order risk below. Consider moving the price table itself to `infra/` as plain config (YAML/JSON) so both `app/` and `agent/` load the same file without a Python import across component boundaries.
- **`infra/seed-incidents/` is separate from `app/flags/`** so the eval harness and demo script can toggle incidents by editing one config file (or setting one env var) without touching application code — this is what "reproducible and demo-safe" means: a judge should be able to see exactly what was toggled by reading a diff, not by reading code.

## Architectural Patterns

### Pattern 1: Deployer Sidecar as the Sole Docker-Socket Holder

**What:** A minimal service (`deployer/`) is the only container in the compose topology with `/var/run/docker.sock` mounted. It exposes one HTTP endpoint that performs exactly one hardcoded operation. Agent K talks to it over the internal Docker network only — the port is never published to the host or internet.

**When to use:** Any time an AI agent's action surface must include "restart/rollback a container" without giving the agent itself root-equivalent host access. This is a much stronger safety property than "the agent promises to only call rollback."

**Trade-offs:** Costs one extra container and one small codebase to maintain, but this cost is exactly what makes Law 2's "sandbox" check verifiable by a judge rather than asserted.

**Concrete implementation guidance (researched):**

1. **Don't rely on `docker-socket-proxy`'s environment-variable filtering as your only safety layer.** Tools like `Tecnativa/docker-socket-proxy` (or its forks — `linuxserver/docker-socket-proxy`) restrict access by *resource class* (`CONTAINERS`, `IMAGES`, `EXEC`, `POST` on/off, etc.), not by *which compose project or service* is targeted. A `docker compose up -d --no-deps app` still needs `CONTAINERS=1` + `POST=1` + likely `IMAGES=1`, which is broad enough to also let a caller start/stop/recreate *any* container on the host, not just `app`. The footgun is assuming the proxy alone gives you "may only touch the `app` service" — it doesn't. That scoping has to live in `deployer`'s own application code (hardcode the target service name and the rollback command; never accept a container/service name from the request body).
2. **Given the above, for a 7-day scope, skip the socket-proxy container** and mount the socket directly into `deployer` — the proxy adds a container and a config surface without buying the scoping guarantee you actually want. If time remains on Day 7, layering `docker-socket-proxy` underneath `deployer` (with `EXEC=0`, `SECRETS=0`, `AUTH=0`, `SWARM=0`, `NODES=0`, `BUILD=0`) is a legitimate defense-in-depth addition, not the primary control.
3. **Authenticate `agent-k → deployer`** with a shared secret (bearer token in an env var both containers read) even though it's an internal network — this stops a compromised `app` container (which sits on the same Docker network for OTLP export) from also being able to call `/rollback` if network segmentation is ever loosened.
4. **The rollback target must not be attacker/LLM-controlled.** `deployer` decides "previous known-good tag" itself (e.g., by reading a small local state file it wrote at the last successful deploy, or from a pinned `PREVIOUS_IMAGE_TAG` env var set at build time) — Agent K's `/rollback` call should carry no image reference at all, just "do it," plus an idempotency/investigation ID for audit correlation. This closes the "what if the policy gate is bypassed and an attacker supplies a malicious tag" class of concern entirely.
5. **Concurrency:** guard `deployer` with an in-memory lock (or file lock) so two overlapping rollback calls can't race `docker compose` commands. Return 409 if a rollback is already in-flight. This is a small addition worth building alongside the endpoint, not an afterthought.
6. **Atomicity, honestly scoped:** true zero-downtime blue-green rollback needs a router/proxy component, which is explicitly out of scope ("no extra microservices"). The realistic and honestly-reportable interpretation of "atomic" here is: one deterministic `docker compose up -d --no-deps --force-recreate app` (or a compose override file swap) that either fully succeeds or fully fails, with a few seconds of expected downtime, followed by the pipeline's own `verify` stage confirming success via a SigNoz query. Report this accurately (brief recreate window) rather than implying hot-swap zero downtime.
7. **No registry pull needed for rollback** — since only two locally-built image tags are ever in play (current, previous), rollback should never depend on network/registry access, which keeps it fast and demo-safe even if OpenRouter or the internet is flaky at demo time.

### Pattern 2: Deterministic Pipeline with Accumulating Evidence State

**What:** A single `InvestigationState` Pydantic model threaded through each stage function. Each stage reads what it needs from the state and returns an updated (or same-type) state — never a bespoke return type per stage. This is the concrete shape of "explicit Python state machine."

**When to use:** Exactly this project's requirement — Law 1 needs the schema fixed before rendering, Law 2 needs a clean gate point, Law 3 needs each stage's duration/cost individually attributable.

**Example:**
```python
class Evidence(BaseModel):
    query: str                 # exact MCP query issued
    signoz_link: str            # deep link — Law 1 requirement
    time_range: tuple[datetime, datetime]
    result_summary: str
    raw_ref: str                 # pointer/id to full result, not embedded wholesale

class Claim(BaseModel):
    text: str
    confidence: float
    evidence: list[Evidence] = []   # empty = renderer must strip (Law 1)
    relationship: Literal["supports", "contradicts", "inconclusive"]

class PolicyVerdict(BaseModel):
    checks: dict[str, bool]      # slo_breach, allowlisted, cooldown_ok,
                                   # confidence_ok, deployment_related, sandboxed
    authorized: bool
    reason: str
    human_recommendation: str | None

class InvestigationState(BaseModel):
    investigation_id: UUID
    incident_trace_id: str | None      # for span-link correlation
    triggering_alert: dict              # raw webhook payload, kept for audit
    evidence: list[Evidence] = []
    claims: list[Claim] = []
    verdict: PolicyVerdict | None = None
    action_result: dict | None = None
    verification: Evidence | None = None
    stage_timings: dict[str, float] = {}
```
Each stage function signature: `def collect(state: InvestigationState) -> InvestigationState`. This makes every stage a pytest target with a hand-built fixture state and no framework machinery to mock.

**Where LLM calls sit, and where they must not:** the only stage that should call an LLM is `hypothesize` (turning evidence into claims). Every other stage — `validate` (strip claims with empty `evidence[]`), `policy_gate` (the six checks), `act` (call deployer), `verify` (re-query MCP and compare), and the link-checker — must be pure code with no model call in the decision path. This is the direct implementation of the constraint already stated in PROJECT.md ("any design that relies on model compliance for a safety property is invalid"). Concretely: `policy_gate.py` should be unit-testable with zero mocks of any LLM client, because it never imports one.

### Pattern 3: Self-Telemetry Without Feedback Loops

**What:** Agent K instruments itself with the same OTel SDK/collector as the monitored app, but as a fully distinct `service.name` (e.g. `agent-k` vs `rag-support-app`), so dashboards, alerts, and the loop breaker's own queries can filter cleanly by service.

**When to use:** Always, for this project — Law 3 requires it.

**Concrete footgun (researched and worth calling out explicitly):** if zero-code/auto-instrumentation for `requests`/`httpx`/`urllib3` is enabled process-wide in the `agent-k` container, and the OTLP exporter itself transports spans over HTTP using one of those libraries, every span export becomes itself an instrumented HTTP call, which becomes a new span, which needs exporting, which is a new span — an exponential/self-referential blowup, not a graceful loop. This is a documented, known category of OTel Python misconfiguration.
**Prevention:** either (a) use the gRPC OTLP exporter (`opentelemetry-exporter-otlp-proto-grpc`) so the export path isn't wrapped by HTTP auto-instrumentation at all, or (b) if using the HTTP exporter, set `OTEL_PYTHON_REQUESTS_EXCLUDED_URLS` / `OTEL_PYTHON_URLLIB3_EXCLUDED_URLS` (or `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS`) to exclude the collector's own OTLP ingest endpoint from auto-instrumentation. Verify this in Day 1, on the *app* container first (it's the same footgun there), since it's much easier to catch with one service running than to debug on Day 6 with two.

**Correlating investigation spans to the incident they're about:** capture the `trace_id` of the evidence that triggered the investigation (from the alert payload if present, or from the first MCP evidence query's result) into `InvestigationState.incident_trace_id`, then attach it as an OTel `Link` on the top-level investigation span:
```python
link = trace.Link(trace.SpanContext(
    trace_id=int(incident_trace_id, 16), span_id=0,
    is_remote=True, trace_flags=trace.TraceFlags(0x01)
))
with tracer.start_as_current_span("investigation", links=[link]) as span:
    ...
```
SigNoz surfaces span links in its trace-detail view, so a human reviewing the incident trace can jump to the investigation trace and back — this is the audit trail the report also renders to Markdown, kept consistent because both come from the same `investigation_id`/`incident_trace_id` pair in `InvestigationState`.

**Distinguishing resource attributes beyond `service.name`:** also set `service.namespace` (e.g. `agent-k` vs `demo-app`) and a custom resource attribute like `agent.role=investigator` so dashboard panels and the loop breaker's own MCP queries can filter without string-matching on trace content.

## Data Flow

### Incident-to-Rollback Flow

```
[incident is live in app]
    ↓ (app emits OTLP continuously)
[SigNoz alert rule evaluates, e.g. every 60s, over a rolling window]
    ↓ fires
[SigNoz Alertmanager → webhook POST → agent-k /webhook/alert]
    ↓ agent-k extracts: alert labels (service name via GROUP BY label),
    ↓ startsAt, fingerprint. Payload does NOT reliably include a ready-made
    ↓ time-range or query — agent-k must derive investigation window as
    ↓ [startsAt - lookback_buffer, now].
[collect] → fixed MCP query set against SigNoz (traces/logs/metrics for
             the labeled service, scoped to the derived window) → Evidence[]
    ↓
[hypothesize] → single OpenRouter call → Claim[] with confidence + evidence refs
    ↓
[validate] → strip any Claim with empty evidence[] (Law 1) → link-checker
             confirms every SigNoz deep link resolves
    ↓
[policy_gate] → six pure checks → PolicyVerdict
    ↓ authorized?                          ↓ not authorized
[act] → deployer POST /rollback      [report] → evidence-linked human
    ↓ (deployer recreates app          recommendation, no action taken
    ↓  with pinned prior tag)
[verify] → re-query MCP, confirm SLO recovered
    ↓
[report] → render Markdown file + emit summary span (with span link to
            incident_trace_id) → SigNoz
```

### Self-Telemetry Flow (parallel, always-on)

```
agent-k (every stage, every LLM call, every MCP call)
    ↓ OTel SDK, service.name=agent-k, distinct from rag-support-app
    ↓ (OTLP export path excluded from HTTP auto-instrumentation — see Pattern 3)
otel-collector (same instance app uses)
    ↓
clickhouse / query-service
    ↓
[SigNoz dashboard: "agent health" panel] and [agent-k's own loop-breaker,
 which queries recent MCP-query-hash counts back through the MCP server —
 this is Agent K reading its own telemetry, a finite closed loop bounded by
 the fixed query set and a max-iterations guard, not an unbounded recursion]
```

### Key Data Flows

1. **Evidence never leaves SigNoz as raw dumps carried in the LLM prompt beyond what's needed.** `collect` should summarize/aggregate before handing to `hypothesize`, both to keep prompts small (cost) and because `Evidence.raw_ref` + `signoz_link` are what make claims checkable — the LLM doesn't need to see everything, it needs to see enough to reason and enough to cite.
2. **Postgres is never queried by `agent-k`.** All app-state visibility comes through telemetry, deliberately, so the investigation story ("what would a human do with only observability access") stays honest and matches what Law 1 can prove.
3. **The webhook is a trigger, not a data source of record.** Once `agent-k` has a service name + rough time window, it re-derives everything else through its own MCP queries — this makes the investigation reproducible even if the webhook payload is thin (which, per SigNoz's Alertmanager-based format, it likely is: no guaranteed query/time-range field).

## Anti-Patterns

### Anti-Pattern 1: Putting the Docker Socket (or Docker CLI) Inside Agent K

**What people do:** mount `/var/run/docker.sock` into the agent container "just for the rollback action," reasoning that the policy gate will stop it from being misused.
**Why it's wrong:** it makes Law 2's "sandbox" check a matter of code discipline inside a component that also runs LLM-influenced logic, rather than a structural guarantee. A prompt-injection or reasoning bug in `hypothesize` would then be one Python call away from arbitrary Docker control.
**Instead:** the deployer sidecar pattern above — Agent K's worst-case blast radius is "makes one authenticated HTTP call to an endpoint that does exactly one hardcoded thing."

### Anti-Pattern 2: Letting the Policy Gate (or Validator) Call an LLM "Just to Double-Check"

**What people do:** add an LLM-based sanity check inside the safety-critical stages ("ask the model if this looks safe to roll back") believing it adds a layer of safety.
**Why it's wrong:** it silently reintroduces model dependency into a safety property, which PROJECT.md explicitly calls a design error. It also makes the gate's outcome non-deterministic and much harder to unit test or explain to a judge.
**Instead:** keep `validate` and `policy_gate` pure functions over already-structured data (`Claim`, `Evidence`, thresholds from config). If a check needs a judgment call, encode the rule (e.g., "confidence >= 0.8"), don't ask a model to render the verdict.

### Anti-Pattern 3: Treating the Webhook Payload as Authoritative for Scope

**What people do:** parse the SigNoz webhook body for an exact time range/query and trust it fully.
**Why it's wrong:** the payload follows the Prometheus Alertmanager shape (`receiver`, `status`, `alerts[].labels/annotations/startsAt/endsAt/fingerprint`, `groupLabels`, `commonLabels`) and does not guarantee a query or time-range field — relying on one that may not exist reliably breaks the investigation trigger exactly when a judge is watching.
**Instead:** use the webhook purely as a trigger + label carrier (service name via a label set on the alert rule's GROUP BY / custom labels), and have `agent-k` derive its own investigation window from `startsAt` plus a configured lookback buffer.

### Anti-Pattern 4: Single-Day Bundling of Deployer + Policy Gate (Locked-Plan Risk)

**What people do:** treat "Law 2" as one day of work covering both the safety-critical sidecar infrastructure and the six-check policy logic, plus wiring and the two-approval/two-denial demo test.
**Why it's wrong:** this is the most safety-critical component in the project and the most schedule-fragile if it's all first-touched on Day 5. See Build Order below.
**Instead:** scaffold `deployer/` (container, socket mount, one hardcoded endpoint, auth) as early as Day 1-2, in parallel with app/telemetry work, since it has zero dependency on the agent's reasoning pipeline — only on the app + versioned images existing.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenRouter | OpenAI-SDK-compatible client, base URL swapped; both `app` (RAG) and `agent-k` (hypothesize) call it independently, each with its own call-site wrapper for GenAI attribute + cost capture | Confirm the pinned free-tier models support `strict` JSON-schema/function-calling structured output before Day 3 — this is required for the RCA schema to come back reliably typed; `instructor`-style validation (retry-on-schema-failure) over raw Pydantic `model_validate` is worth the small dependency given free-tier models can be flaky on strict adherence. |
| SigNoz (via Foundry) | Deployed as a unit via `casting.yaml` + `foundryctl cast`; app and agent-k join its Docker network for OTLP export; MCP server and webhook are the only two channels `agent-k` uses to talk to it | Do not hand-edit Foundry's generated `pours/` compose output — extend via a separate `docker-compose.yml` that references the same external network (`docker network` created by Foundry's compose) so `foundryctl cast` remains the reproducible, judge-rerunnable entrypoint. Verify Foundry's exact "extra services" mechanism (moldings) directly against `SigNoz/foundry` docs early on Day 1, since this determines whether `app`/`agent-k`/`deployer`/`postgres` live in Foundry's compose file or a sibling one — documentation on this was not conclusively retrievable in this research pass (flagged as a gap below). |
| SigNoz MCP server | `agent-k` as MCP client (stdio or HTTP transport); server holds a SigNoz API key, agent-k holds no direct SigNoz credentials beyond what the MCP transport requires | Restrict `agent-k`'s MCP client wrapper to a fixed allowlist of read/query tool names (`signoz_search_traces`, `signoz_aggregate_logs`, `signoz_query_metrics`, `signoz_get_trace_details`, etc.) — never call the `_create_`/`_update_`/`_delete_` tools from the investigation pipeline, even though the server exposes them (those are for setup/admin use, done once via `infra/`). |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `app` ↔ `postgres` | direct DB connection (asyncpg/SQLAlchemy) | Only `app` (and seed scripts) ever connects here. |
| `app` ↔ SigNoz | OTLP push (traces/metrics/logs) | One-directional; app has no SigNoz query access and no knowledge of `agent-k`. |
| SigNoz ↔ `agent-k` | (a) webhook push on alert fire, (b) MCP query pull | Two separate channels with different semantics: (a) triggers, (b) informs. Keep them in separate modules (`webhook.py` vs `mcp_client.py`). |
| `agent-k` ↔ `deployer` | HTTP, one authenticated POST endpoint, internal network only | The sandbox boundary. No other path between these two containers should exist. |
| `agent-k` ↔ OpenRouter | HTTPS, external | Single call-site module (`agent/llm.py`) so every call is uniformly instrumented for Law 3 — do not scatter OpenRouter calls across pipeline stages. |
| `deployer` ↔ Docker daemon | Unix socket (direct mount, or via `docker-socket-proxy` if added later) | See Deployer Sidecar Pattern above for scoping guidance. |

## Build Order and Dependency Graph

The locked 7-day plan (Day1 SigNoz+app+OTel → Day2 SLOs/alerts/markers/failure flags → Day3 agent workflow+MCP+RCA schema → Day4 Law1 → Day5 Law2 → Day6 Law3 → Day7 eval+demo) is directionally sound — SigNoz must exist before anything can be queried, the pipeline shape must exist before individual Laws can be layered onto it, and eval/demo must come last. The genuine dependency graph confirms the macro order but surfaces four risks worth resolving before they land on the day they're currently scheduled.

### Confirmed Correct Dependencies

- Day1 (SigNoz + app + OTel) must precede everything — no evidence exists to collect otherwise.
- Day3's `hypothesize`/`collect` stages need Day1's telemetry and Day2's seeded incidents to have anything meaningful to reason about.
- Day4 (Law 1: evidence validator, link checker) must precede Day5 (Law 2: policy gate), since the policy gate's "confidence" check consumes already-validated claims.
- Eval (Day7) must come last — it needs the full pipeline, both approvals and both denials, working.

### Ordering Risks

**Risk 1 — Cost computation is framed as Day 6 (Law 3) but Day 2's cost SLO/alert needs it first.**
The Key Decision "cost is computed from token counts against a configured price table" is written as if it belongs to Agent K's own Law 3 cost watchdog. But Incident 2's cost SLO breach — evaluated and alerted on Day 2 — is about the *monitored app's* OpenRouter spend, not Agent K's. A cost metric/alert cannot be defined on Day 2 without the price-table lookup already existing. **Mitigation:** extract the price-table module (`agent/cost.py` or a shared `infra/pricing.yaml`) as a small piece of Day 1 work, used by the app's own GenAI-attribute instrumentation immediately, and reused unmodified by Agent K's Law 3 watchdog on Day 6. Do not let "cost computation" be a Day 6 build item — it's a Day 1 build item with a Day 6 consumer.

**Risk 2 — Day 5's Law 2 bundles the safety-critical sidecar, the policy logic, and end-to-end demo validation into one day.**
`deployer/` has zero dependency on the agent's reasoning pipeline (only on `app` + versioned images existing), so scaffolding it on Day 5 for the first time is unnecessary schedule risk on the single most safety-critical component. **Mitigation:** build and smoke-test `deployer/` (container, socket mount, one hardcoded rollback endpoint, auth, concurrency lock) on Day 1-2, in parallel with app/telemetry work. Day 5 then only has to write the six-check policy module and wire it to an already-proven sidecar — a much smaller, lower-risk day.

**Risk 3 — Day 6's loop breaker presupposes an iteration Day 3's pipeline design may not have.**
PROJECT.md's Key Decision rationale for "no agent framework" states "the investigation uses a fixed query set" — implying `collect` is a deterministic, non-LLM-directed sequence of MCP queries. But Law 3 requires "a loop breaker that hashes MCP queries and halts on excessive repetition," which only makes sense if there is a loop where repetition could occur (e.g., `hypothesize` triggering a bounded round of follow-up `collect` calls). **This is a real design decision Day 3 must make explicitly, not one Day 6 can retrofit painlessly.** Mitigation: on Day 3, decide and document whether `collect`/`hypothesize` can loop (recommend: yes, bounded to a small fixed max, e.g. 2 extra rounds, specifically to justify Incident-driven "need more evidence" cases) and if so, build the query-hash tracking as cheap infrastructure in `collect.py` on Day 3 even though the halt-and-escalate *policy* (watchdog alert, escalation) is Day 6 work layered on top of data already being recorded.

**Risk 4 — Day 6's per-LLM-call instrumentation should be built alongside Day 3's LLM call site, not deferred.**
Since the state-machine architecture decision explicitly justifies itself by "owning every LLM call site... makes Law 3's exact token, cost, and duration accounting possible," the instrumentation hooks (span attributes for `gen_ai.usage.input_tokens`/`output_tokens`, duration, cost via Risk 1's shared module) are naturally part of building `agent/llm.py` on Day 3 when `hypothesize` first calls OpenRouter — not something bolted on three days later. **Mitigation:** instrument `agent/llm.py` fully on Day 3 (attributes + cost + duration emitted as spans/metrics); Day 6 then only adds the *threshold check and halting behavior* (cost watchdog logic) on top of telemetry that has already been flowing and been debugged for three days. This also gives Day 3-5 development visibility into actual free-tier spend, which is otherwise flown blind.

### Recommended Adjusted Sequencing Within the Locked Days

The locked day *labels* (Day1...Day7) and their headline deliverables don't need to change to address the above — what needs to change is which day *first touches* certain code:

| Locked Day | Headline deliverable (unchanged) | Should also first-touch (moved earlier than the headline implies) |
|---|---|---|
| Day 1 | SigNoz + app + OTel | Shared price-table module (Risk 1); `deployer/` skeleton (Risk 2, can start Day 1 end / Day 2) |
| Day 2 | SLOs/alerts/markers/failure flags | `deployer/` smoke-tested against a manually-triggered rollback (Risk 2) |
| Day 3 | Agent workflow + MCP + RCA schema | Explicit collect/hypothesize loop-or-not decision + query-hash tracking scaffold (Risk 3); full LLM call-site instrumentation (Risk 4) |
| Day 4 | Law 1 (validator, link checker) | — |
| Day 5 | Law 2 (policy gate + wiring + 2 approvals/2 denials) | Only wiring, since `deployer/` already exists and is proven |
| Day 6 | Law 3 (watchdog thresholds, loop-breaker halting/escalation) | Only the halting/threshold policy, since instrumentation already flows |
| Day 7 | Eval + demo | — |

## Sources

- [SigNoz MCP Server README](https://github.com/SigNoz/signoz-mcp-server/blob/main/README.md) — MEDIUM confidence (WebFetch-summarized, tool list should be spot-checked against the actual server version pinned in `casting.yaml`)
- [SigNoz Webhook Notification Channel docs](https://signoz.io/docs/alerts-management/notification-channel/webhook/) — MEDIUM confidence; payload shape corroborated as Prometheus Alertmanager format by multiple independent sources
- [SigNoz Routing Policies docs](https://signoz.io/docs/alerts-management/routing-policy/) — HIGH confidence for label-based routing; LOW confidence / gap on group_wait/group_interval timing controls (not found in retrieved docs — verify directly in the SigNoz UI on Day 2)
- [SigNoz Understanding Alert Evaluation Patterns](https://signoz.io/docs/alerts-management/user-guides/understanding-alert-evaluation-patterns/) — HIGH confidence: default 1-minute eval cadence, rolling/cumulative windows, minimum-data-point flapping guard
- [Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) — HIGH confidence, official README, widely used pattern
- [SigNoz Foundry — getting-started.md](https://github.com/SigNoz/foundry/blob/main/docs/getting-started.md) and [Foundry repo](https://github.com/SigNoz/foundry) — MEDIUM confidence; minimal casting.yaml structure confirmed, but the exact mechanism for adding non-SigNoz services (moldings) was not conclusively retrieved — treat as a Day 1 verification task, not an assumption
- [OpenTelemetry Traces concepts — Span Links](https://opentelemetry.io/docs/concepts/signals/traces/) and [span links practical guide with SigNoz](https://dev.to/clericcoder/mastering-trace-analysis-with-span-links-using-opentelemetry-and-signoz-a-practical-guidepart-2-1amc) — HIGH/MEDIUM confidence respectively
- [OpenTelemetry Python zero-code configuration](https://opentelemetry.io/docs/zero-code/python/configuration/) — HIGH confidence on `OTEL_PYTHON_*_EXCLUDED_URLS` / `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` env vars for preventing exporter self-instrumentation feedback
- [OpenTelemetry Generative AI semantic conventions overview](https://opentelemetry.io/blog/2024/otel-generative-ai/) — HIGH confidence for `gen_ai.*` attribute names
- [Instructor: Structured outputs with OpenRouter](https://python.useinstructor.com/integrations/openrouter/) and [OpenRouter API reference](https://openrouter.ai/docs/api_reference/overview) — MEDIUM confidence; verify the specific pinned free-tier models' structured-output support directly before Day 3 (model identity is explicitly expected to change per PROJECT.md)

## Gaps to Address

- **Foundry's exact mechanism for co-locating non-SigNoz services** (app, agent-k, deployer, postgres) on the same Docker network as its generated compose output was not conclusively confirmed from documentation retrieved in this pass. Resolve directly against `SigNoz/foundry` repo (`docs/concepts/moldings.md` and `examples/`) on Day 1 before finalizing the top-level `docker-compose.yml` layout.
- **SigNoz webhook payload's exact default grouping delay** (Alertmanager's `group_wait`/`group_interval`, typically defaulting to ~30s/5min upstream) and whether SigNoz's routing policy UI exposes these for tuning was not conclusively confirmed. This is a live demo-reliability risk — verify on Day 2, and build a manual `/demo/trigger` fallback endpoint on `agent-k` regardless, so the live demo does not depend on webhook timing being fast enough in the room.
- **Whether the pinned free-tier OpenRouter models reliably honor `strict` structured output / function calling** for the RCA schema is unverified against current model behavior (training-data-era knowledge only) — PROJECT.md already anticipates this with `cohere/north-mini-code:free` as a documented fallback; treat schema-adherence testing as a first task on Day 3, not an assumption.

---
*Architecture research for: Agent K — evidence-first, safety-gated, self-observing incident-response agent*
*Researched: 2026-07-20*
