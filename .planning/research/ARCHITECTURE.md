# Architecture Research

**Domain:** Code-enforced incident-response agent + monitored RAG service (observability/AgentOps hackathon build)
**Researched:** 2026-07-20
**Confidence:** MEDIUM (SigNoz MCP tool surface cross-verified across 2 independent sources; remaining findings are single-source WebSearch synthesis — treat implementation specifics as directionally correct, verify exact APIs against installed versions during build)

## Standard Architecture

### System Overview

Two independent OS processes on one host, both instrumented into one shared SigNoz backend, connected by three thin wires: a webhook (SigNoz→Agent K), an MCP HTTP connection (Agent K→SigNoz), and a filesystem/subprocess mutation (Agent K→RAG host config). There is no shared database, no shared memory, no framework coupling — the only integration surface between "the thing being watched" and "the thing watching it" is SigNoz itself plus the docker-compose file on disk. This is deliberate: it is what makes Law 1/2/3 auditable, and it's what keeps the two processes buildable/testable in isolation.

```
┌───────────────────────────────────────────────────────────────────────┐
│  PROCESS 1: RAG Support Service (FastAPI, uvicorn, port 8000)         │
├───────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐    │
│  │ /ask        │  │ Feature    │  │ Retrieval  │  │ Prompt +     │    │
│  │ endpoint    │→ │ Flag Store │→ │ (pgvector) │→ │ Generation   │    │
│  │             │  │ (in-mem)   │  │            │  │ (Groq LLM)   │    │
│  └────────────┘  └─────┬──────┘  └─────┬──────┘  └──────┬───────┘    │
│                        │ /admin/flags   │                │            │
│                        │ (toggle HTTP)  │                │            │
│                 ┌──────┴────────────────┴────────────────┘            │
│                 │  OTel SDK: traces + metrics + logs + gen_ai.* attrs │
├─────────────────┴─────────────────────────────────────────────────────┤
│                 OTLP export → OTel Collector (or direct OTLP)         │
└─────────────────┬───────────────────────────────────────────────────┬─┘
                   │                                                   │
                   ▼                                                   │
┌───────────────────────────────────────────────────────────────────┐  │
│               SigNoz (self-hosted via Foundry, one instance)      │  │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │  │
│  │ Traces    │ │ Metrics   │ │ Logs      │ │ Dashboard │ │ Alerts │ │  │
│  │ (Query    │ │ (Query    │ │ (Query    │ │ (4        │ │ (webhook│ │  │
│  │ Builder)  │ │ Builder)  │ │ Builder)  │ │ sections) │ │ channel)│ │  │
│  └───────────┘ └───────────┘ └──────────┘ └──────────┘ └───┬────┘ │  │
│                                                              │      │  │
│  ┌────────────────────────────────────────────────────┐    │      │  │
│  │  SigNoz MCP Server (HTTP mode, TRANSPORT_MODE=http)  │←───┼──────┼──┐
│  │  40+ tools: search_traces, aggregate_logs,           │    │      │  │
│  │  query_metrics, get_alert_history, list_services...  │    │      │  │
│  └───────────────────────┬────────────────────────────┘    │      │  │
└──────────────────────────┼──────────────────────────────────┼──────┘  │
                            │ MCP calls (evidence queries)      │ POST   │
                            │                                   │ webhook│
                            ▼                                   ▼        │
┌───────────────────────────────────────────────────────────────────┐  │
│  PROCESS 2: Agent K (FastAPI, uvicorn, port 8100)                 │  │
├───────────────────────────────────────────────────────────────────┤  │
│  ┌──────────────┐  ┌─────────────────────────────────────────┐   │  │
│  │ /webhook/    │→ │  State Machine (plain Python, sync loop) │   │  │
│  │ alert        │  │  RECEIVED→INVESTIGATING→HYPOTHESIZING→   │   │  │
│  │ (validates,  │  │  POLICY_CHECK→(ACTING|REPORTING)→        │   │  │
│  │ enqueues)    │  │  VERIFYING→REPORTED                       │   │  │
│  └──────────────┘  └──────┬──────────┬──────────┬────────────┘   │  │
│                            │          │          │                 │  │
│                     ┌──────▼───┐ ┌────▼─────┐ ┌──▼──────────┐    │  │
│                     │ MCP      │ │ Law 2     │ │ Rollback     │    │  │
│                     │ Client   │ │ Policy    │ │ Executor     │────┼──┘
│                     │ (evidence)│ │ Module    │ │ (subprocess) │  (mutates
│                     └──────────┘ │ (code,    │ └──────────────┘   docker-
│                                  │ no LLM)   │                     compose.yml
│                     ┌──────────┐ └───────────┘  ┌──────────────┐  on RAG
│                     │ Loop     │                 │ Report Store │  service
│                     │ Breaker/ │                 │ (JSON RCA)   │  host)
│                     │ Cost     │                 └──────┬───────┘
│                     │ Watchdog │                        │
│                     └──────────┘                 ┌──────▼───────┐
│                                                    │ /report/{id} │
│  All state-machine transitions, MCP calls,        │ HTML page    │
│  LLM calls, policy decisions → OTel spans/metrics │ (Jinja2)     │
│  → same OTLP path → SigNoz                        └──────────────┘
└───────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| RAG Service (`app/`) | Serve `/ask`, retrieve from pgvector, call LLM, emit OTel telemetry, expose failure-flag admin API | FastAPI + SQLAlchemy/psycopg + pgvector + `opentelemetry-instrumentation-fastapi` |
| Feature Flag Store | In-process, in-memory dict of `flag_name → {enabled, params}`, mutated via `/admin/flags/{name}`, read on every request path that needs it | Python singleton/module-level dict guarded by a lock; no external service |
| pgvector datastore | Single Postgres instance holding both support-doc rows and their embedding vectors | `pgvector` extension, one table, cosine/L2 index |
| OTel SDK (both processes) | Turn code into spans/metrics/logs with correct semantic conventions (`gen_ai.*`, `http.*`, custom `agentk.*`) | `opentelemetry-sdk` + OTLP exporter, auto-instrumentation + manual spans for business logic |
| SigNoz | Single source of truth for all telemetry; hosts Query Builder, dashboards, alerting, and the MCP server | Self-hosted via Foundry/`casting.yaml` |
| SigNoz MCP Server | Exposes SigNoz's query surface as callable MCP tools over HTTP | `signoz/signoz-mcp-server` Docker image, `TRANSPORT_MODE=http` |
| Agent K webhook receiver | Accepts SigNoz's Alertmanager-shaped POST, validates/dedupes, starts a state-machine run | FastAPI endpoint, one route |
| Agent K state machine | Drives RECEIVED→...→REPORTED; the only place that decides "what next" | Plain Python class/function with an explicit `State` enum, no framework |
| MCP Client wrapper | One place all SigNoz MCP tool calls go through — wraps each call in a span, hashes the query for loop detection | `mcp` Python SDK `ClientSession` over `streamablehttp_client` |
| Law 2 Policy Module | Pure function(s): evidence + proposed action → allow/deny + reason, no LLM call inside it | Plain Python, unit-testable in isolation |
| Rollback Executor | Edits `docker-compose.yml` image tag on the RAG service's compose file, runs `docker compose up -d`, creates a SigNoz deployment marker, re-queries for recovery | `subprocess.run(["docker","compose","up","-d"], ...)` + `PyYAML` for the edit |
| Report Store + HTML renderer | Persists the structured RCA JSON, serves it as an HTML page with deep links back into SigNoz | FastAPI route + Jinja2 template, JSON on disk or SQLite (no need for Postgres here) |
| Loop Breaker / Cost Watchdog | Cross-cutting checks invoked from inside the state machine's MCP-call and LLM-call wrappers | Simple counters/hash-set per investigation run |

## Recommended Project Structure

```
agent-k/                          # monorepo root (per PROJECT.md decision)
├── casting.yaml                  # Foundry deployment spec (SigNoz + collector + compose)
├── casting.yaml.lock
├── docker-compose.yml            # RAG service + Postgres/pgvector (the file Agent K mutates)
├── rag-service/
│   ├── app/
│   │   ├── main.py               # FastAPI app, /ask, /health
│   │   ├── flags.py              # in-memory FeatureFlagStore + /admin/flags/* routes
│   │   ├── retrieval.py          # pgvector query step (custom span)
│   │   ├── generation.py         # prompt-construction + LLM call step (gen_ai.* spans)
│   │   ├── llm_client.py         # OpenAI-compatible client, provider via env var
│   │   ├── db.py                 # SQLAlchemy engine/session, pgvector setup
│   │   ├── otel.py               # OTel SDK bootstrap (traces/metrics/logs)
│   │   └── failure_modes/        # the 4 seeded scenarios, gated by flags.py
│   │       ├── prompt_regression.py
│   │       ├── retry_storm.py
│   │       ├── retrieval_latency.py
│   │       └── pool_exhaustion.py
│   ├── corpus/                   # ~50-200 synthetic support docs + seed script
│   └── Dockerfile
├── agent-k/
│   ├── app/
│   │   ├── main.py                # FastAPI app, /webhook/alert, /report/{id}
│   │   ├── otel.py                 # OTel SDK bootstrap (mirrors rag-service/app/otel.py)
│   │   ├── statemachine/
│   │   │   ├── states.py           # State enum + transition table
│   │   │   ├── runner.py           # the actual loop: drives states end to end
│   │   │   ├── investigate.py      # hypothesis generation + MCP evidence gathering
│   │   │   ├── confidence.py       # hybrid confidence: LLM propose + code recalibrate
│   │   │   ├── loop_breaker.py     # query-hash tracking, repeat detection
│   │   │   └── cost_watchdog.py    # token/cost budget tracking
│   │   ├── mcp_client.py           # thin wrapper over `mcp` SDK ClientSession, one call-site
│   │   ├── policy.py               # Law 2: pure function(s), unit-tested standalone
│   │   ├── rollback.py             # docker-compose.yml edit + `docker compose up -d` + marker
│   │   ├── report.py               # RCA schema (Law 1 claim/evidence), renderer, link checker
│   │   └── llm_client.py           # same provider-abstraction pattern as rag-service
│   ├── templates/report.html       # Jinja2 HTML report page
│   └── Dockerfile
├── infra/
│   ├── otel-collector-config.yaml  # (if using a collector rather than direct OTLP)
│   └── signoz-dashboard.json       # exported hand-built dashboard
├── eval/
│   └── run_scenarios.py            # 3-runs-per-incident evaluation harness
└── docs/blog/                      # submission write-up
```

### Structure Rationale

- **`rag-service/` and `agent-k/` are siblings, not nested:** they are separate deployables (separate Dockerfiles, separate uvicorn processes, separate OTel service names). Nesting one inside the other would blur the "two-process system" boundary the whole safety story depends on.
- **`agent-k/app/mcp_client.py` and `agent-k/app/policy.py` are single-purpose files, not folders:** both are judged directly (Law 1 evidence-visibility, Law 2 code-enforcement) — keeping each to one importable, individually unit-testable module makes both easy to point a judge at and easy to test in isolation from the state machine.
- **`failure_modes/` lives inside the RAG service, gated by `flags.py`:** failure injection is a property of the monitored app, not of Agent K — Agent K must detect these purely through telemetry/evidence, never through direct code awareness of which flag is on. This boundary is itself part of what's being tested.
- **`otel.py` duplicated in both services rather than shared as a library:** for a 7-day build with a team new to OTel, a shared internal package adds packaging overhead (versioning, install path) for marginal DRY benefit; near-identical bootstrap code in two files is fine and easier to debug per-service.
- **`eval/` is separate from both apps:** the evaluation harness drives both processes from outside (fires flags, fires alerts, reads reports) — it should not import internals from either app, only hit their HTTP surfaces, so it stays honest as a black-box test.

## Architectural Patterns

### Pattern 1: State Machine as the Only Control-Flow Authority

**What:** Agent K's entire investigation/action/report lifecycle is one explicit `State` enum with a deterministic transition table. The LLM is called *from inside* specific states (e.g., `HYPOTHESIZING` asks the LLM to propose a root cause given evidence already gathered) but never decides *which state comes next* — that's always code.
**When to use:** Any time an "agent" must have externally auditable, code-enforced behavior boundaries (Laws 1/2/3 here) rather than emergent LLM-driven control flow.
**Trade-offs:** More boilerplate than an agent framework's loop; but a framework (LangGraph etc.) would hide the very transitions this project needs to prove are code-enforced, and the team has zero framework experience — net faster and safer to hand-roll for 7 days.

**Example:**
```python
class State(Enum):
    RECEIVED = auto()
    INVESTIGATING = auto()
    HYPOTHESIZING = auto()
    POLICY_CHECK = auto()
    ACTING = auto()
    VERIFYING = auto()
    REPORTED = auto()
    INCOMPLETE = auto()  # loop-breaker / cost-watchdog exit

def run(alert: Alert) -> Report:
    state = State.RECEIVED
    ctx = InvestigationContext(alert)
    while state not in (State.REPORTED, State.INCOMPLETE):
        with tracer.start_as_current_span(f"agentk.state.{state.name}"):
            state, ctx = TRANSITIONS[state](ctx)  # each handler is a pure-ish function
    return render_report(ctx)
```

### Pattern 2: Single Call-Site Wrapper for the MCP Client (Law 1 + Law 3 enforcement point)

**What:** Every SigNoz MCP tool call goes through one function (`mcp_client.query(tool, args)`), which: opens a span, hashes `(tool, args)` for the loop breaker, records duration/success/failure as metrics, and returns a structured `Evidence` object carrying a SigNoz deep link back to the query — never raw unstructured text.
**When to use:** Whenever every external call an agent makes must be individually visible in telemetry and individually checkable for repeats — exactly the Law 1/3 requirement here.
**Trade-offs:** Adds one layer of indirection vs. calling the MCP SDK directly from investigation code; the indirection is the point — it's what makes the loop breaker and evidence-schema enforcement possible without threading that logic through every call site.

**Example:**
```python
async def query(tool: str, args: dict) -> Evidence:
    query_hash = hash_query(tool, args)
    loop_breaker.check(query_hash)  # raises LoopDetected if over threshold
    with tracer.start_as_current_span("agentk.mcp.query", attributes={"mcp.tool": tool}):
        result = await mcp_session.call_tool(tool, arguments=args)
    return Evidence.from_mcp_result(tool, args, result, signoz_base_url=SIGNOZ_URL)
```

### Pattern 3: Deterministic Policy Gate Between Proposal and Execution

**What:** The LLM (inside `HYPOTHESIZING`) may *propose* "rollback is the fix" with a confidence score, but that proposal is inert data until `policy.py::evaluate(proposal, evidence, history) -> Decision(allow: bool, reason: str)` runs — a pure function with no model call inside it, checking: allowlist membership (exactly one action exists), SLO/burn-rate breach confirmed by evidence, cooldown window, confidence threshold, deployment-related cause, sandbox scope. Only `Decision(allow=True)` reaches the executor.
**When to use:** Any agent action with real side effects. Matches the field's converging best practice (allowlist + pre-execution code-enforced check, separate from model reasoning) found across current agent-guardrail literature.
**Trade-offs:** Requires the confidence/evidence schema to be stable and well-typed before the policy module can be written — meaning Law 1's evidence schema is a hard dependency of Law 2, not parallel work.

## Data Flow

### Full Alert → Report Pipeline

```
[1] Alert fires in SigNoz (burn-rate / SLO rule crosses threshold)
      ↓ (SigNoz Alertmanager groups + POSTs, ~5min batch window by default —
         reduce grouping interval for demo responsiveness)
[2] POST → Agent K /webhook/alert
      body: {receiver, status, alerts:[{labels, annotations, startsAt, fingerprint}], ...}
      ↓ validate shape, dedupe by fingerprint, transition RECEIVED → INVESTIGATING
[3] State machine loop begins; each MCP call:
      Agent K → mcp_client.query(tool, args) → SigNoz MCP Server (HTTP) → SigNoz query engine
      ← Evidence{type, query, time_range, link, raw_result} ← back to Agent K
      (repeated N times: search_traces, aggregate_logs, query_metrics, get_alert_history,
       list_services/get_service_top_operations, get_trace_details for deployment markers)
      every call individually spanned + hashed by loop_breaker
[4] HYPOTHESIZING: LLM call (Groq) given accumulated evidence → proposes claim + confidence
      ↓ confidence.py recalibrates: code adjusts LLM's self-reported confidence based on
         evidence strength (deployment marker present? error-rate delta magnitude? etc.)
[5] POLICY_CHECK: policy.py::evaluate(claim, evidence, action_proposal) → Decision
      allow=False → skip to [7] REPORTING (no action taken, report says why)
      allow=True  → [6] ACTING
[6] ACTING: rollback.py
      - reads docker-compose.yml on RAG service host, captures current image tag
      - writes previous-known-good tag into docker-compose.yml
      - subprocess: `docker compose up -d`
      - creates a SigNoz deployment marker (via MCP or SigNoz API) for the rollback itself
      - waits a fixed window
      - re-queries SigNoz (same MCP client) to check whether the SLO/error-rate recovered
      ↓ VERIFYING → outcome recorded (recovered / not recovered / inconclusive)
[7] REPORTING: report.py
      - assembles structured RCA: claims (each with confidence + evidence[] with type/
        query/time_range/link), policy decision + reason, action taken (or not) + outcome
      - link checker resolves every evidence link against the live SigNoz instance;
        any claim whose evidence fails to resolve is stripped before render (Law 1 enforced
        at render time, not just at claim time)
      - persisted (JSON) + rendered as HTML at /report/{id}
[8] Throughout [1]-[7]: every state transition, MCP call, LLM call (with gen_ai.* token/cost
      attributes), policy decision, and action attempt is itself emitted as an OTel span/metric
      from Agent K's own OTel SDK → same SigNoz instance (Law 3) — so the agent's own behavior
      shows up on the "agent health" dashboard section in near-real-time as it investigates
      the RAG service's problem.
```

### Key Data Flows

1. **Telemetry flow (continuous, both processes → SigNoz):** RAG service and Agent K each run their own OTel SDK bootstrap, exporting OTLP (traces, metrics, logs) either directly to SigNoz's OTLP endpoint or via an OTel Collector sidecar. This is the substrate everything else depends on — nothing else works until this flows correctly, which is why it must be built and demoed first.
2. **Evidence flow (per-investigation, Agent K ⇄ SigNoz via MCP):** one-directional request/response per MCP tool call; Agent K never writes to SigNoz through MCP except deployment markers/alert creation — it's primarily a read path for evidence-gathering, one call per hypothesis-relevant question.
3. **Control flow (one-shot per incident, SigNoz → Agent K → RAG service host):** webhook triggers the whole run; the only place Agent K writes outside its own process is `docker-compose.yml` + the `docker compose up -d` subprocess call — a single, narrow, auditable mutation surface.
4. **Report flow (Agent K → judge/human):** JSON RCA → HTML render, with every fact traceable back to a SigNoz deep link — this is the artifact judges/evaluators actually read, so it must faithfully reflect what the evidence/policy/action layers produced, nothing invented at render time.

## Scaling Considerations

Not a scaling concern for this project — single host, single incident at a time, 7-day hackathon scope. Included for completeness per template, but treat as explicitly out of scope (see PROJECT.md Out of Scope).

| Scale | Architecture Adjustments |
|-------|---------------------------|
| Hackathon demo (this project) | Single host, sequential incidents, in-memory flags, direct docker-compose access — exactly as scoped |
| If ever extended: concurrent incidents | State machine would need per-incident isolation (currently fine since a queue/lock isn't specified — investigations must be run one-at-a-time or the loop breaker/cooldown state needs incident-keying) |
| If ever extended: multi-host rollback | Direct docker-compose access breaks; would need an actual deployment API/agent-per-host — explicitly out of scope for this build |

### Scaling Priorities

Not applicable — do not spend build time here. If forced to name a first bottleneck: concurrent alert webhooks arriving while an investigation is in flight (no queueing is specified in PROJECT.md) — worth a one-line guard (reject/queue a second webhook while `state != REPORTED/INCOMPLETE`) so the demo doesn't produce two interleaved investigations, but not worth more than that.

## Anti-Patterns

### Anti-Pattern 1: Letting the LLM Decide Control Flow

**What people do:** Wrap the whole investigation in an agent-framework loop (ReAct-style, LangGraph, etc.) where the model decides which tool to call next and when to stop.
**Why it's wrong:** Directly contradicts the project's own explicit decision (plain Python state machine, no framework) and undermines Law 1/2/3 — if the model decides control flow, "code-enforced" becomes "code-assisted," which is a different and weaker claim, and is exactly the framing judges are told to distrust ("nothing is trust-the-model").
**Do this instead:** Model proposes (hypothesis, confidence, action) as structured data at specific, code-chosen points; code decides state transitions and gates every consequential decision (policy check, loop breaker, cost watchdog).

### Anti-Pattern 2: Treating the Feature-Flag Toggle and the Deployment Marker as the Same Event

**What people do:** Since flags are the mechanism for "deploying" failure scenarios, it's tempting to auto-create a SigNoz deployment marker on every flag toggle.
**Why it's wrong:** PROJECT.md explicitly calls out that flag toggle and deployment-marker creation must be *separable*, conflated only deliberately for specific incidents (Incident 1/2). If every flag toggle always creates a marker, Agent K's "deployment-related cause" policy check becomes trivially always-true and the evaluation stops being meaningful — it would no longer distinguish "flag flipped without a real deploy" from "genuine deploy-caused regression."
**Do this instead:** Marker creation is its own explicit call (in the incident-seeding script, or manually in the demo script), decoupled from `/admin/flags/*`, wired per-scenario rather than globally.

### Anti-Pattern 3: Direct String/YAML Munging Without Capturing the Prior State

**What people do:** `sed`/naive string-replace the image tag in `docker-compose.yml` and immediately run `docker compose up -d` without recording what the tag was before the edit.
**Why it's wrong:** Breaks the ability to verify "rollback = revert to the immediately preceding version" as a provable claim in the report, and makes a rollback-of-a-bad-rollback impossible to reason about; also YAML string-replace is fragile against comments/formatting drift.
**Do this instead:** Parse with `PyYAML`, read and log the current tag before mutating, write back with the library (not string replace), and record `{previous_tag, new_tag, timestamp}` as both a SigNoz deployment marker and a field in the eventual report.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|----------------------|-------|
| SigNoz (self-hosted via Foundry) | OTLP ingestion (traces/metrics/logs) from both processes; MCP server (HTTP mode) for Agent K's evidence queries; webhook notification channel for alert delivery to Agent K | Requires SigNoz v0.118.0+ for alert-history MCP tools per SigNoz MCP server README — verify installed Foundry version supports this before relying on `signoz_get_alert_history` |
| Groq (LLM provider) | OpenAI-compatible client, used by both RAG service (answer generation) and Agent K (hypothesis reasoning) | Behind one provider-abstraction module per PROJECT.md; both services should emit `gen_ai.*` attributes on every call |
| SigNoz MCP Server | Run as its own container (`signoz/signoz-mcp-server:latest`, `TRANSPORT_MODE=http`) alongside SigNoz; Agent K connects over HTTP using the official `mcp` Python SDK's streamable-HTTP client | Prefer HTTP transport over stdio-subprocess — avoids Agent K needing to manage a child process lifecycle for the MCP server |
| Docker Engine (host) | Agent K shells out via `subprocess` to `docker compose up -d` in the RAG service's directory | Not a "service" so much as direct host access — the whole "sandbox" is the fact that only one compose file, one action, is ever touched |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|----------------|-------|
| RAG service ↔ Agent K | None directly — only via SigNoz (telemetry) and the docker-compose file (control) | This is the core architectural property: the monitored app has zero awareness of Agent K; Agent K has zero in-process awareness of RAG internals, only what telemetry exposes |
| Agent K webhook receiver ↔ state machine | In-process function call (enqueue or direct synchronous invoke, given single-incident-at-a-time scope) | Keep synchronous for the demo — no task queue needed at this scale |
| State machine ↔ MCP client wrapper | In-process, `await mcp_client.query(...)` | Single call-site as described in Pattern 2 |
| State machine ↔ Policy module | In-process, pure function call, no I/O inside `policy.py` | Enables policy.py to be unit-tested with zero mocking |
| Policy module ↔ Rollback executor | In-process, only invoked when `Decision.allow == True` | Executor should itself re-check allowlist membership defensively (never trust caller alone) as a second gate |
| Feature flag store ↔ RAG request handlers | In-process, read-through on every relevant request | No pub/sub needed at single-process scale despite what general feature-flag literature suggests for larger systems |

## Suggested Build Order (dependency-ordered, informs 7-day roadmap)

1. **OTel instrumentation skeleton on the RAG service** (traces/metrics/logs → SigNoz, even trivial ones). Nothing downstream is demoable or debuggable without telemetry existing first — and the team has zero OTel experience, so this needs the most ramp-up buffer.
2. **SigNoz self-hosted via Foundry (`casting.yaml`)**, confirmed receiving RAG service telemetry. Must exist before dashboards, alerts, or MCP server can be wired.
3. **RAG service core (retrieval + generation + pgvector + synthetic corpus)**, fully instrumented with `gen_ai.*` attributes. This is also the team's Docker on-ramp.
4. **Feature-flag service + the 4 seeded failure scenarios**, demoable live via `/admin/flags`. Blocks everything downstream that needs a real incident to investigate — Agent K cannot be meaningfully built/tested against nothing happening.
5. **SigNoz dashboard + SLO/burn-rate alerts + webhook notification channel**, hand-built in UI, confirmed firing a real webhook POST when a flag-triggered incident occurs. This is the last piece of "process 1's world" and the trigger for process 2.
6. **SigNoz MCP server stood up (HTTP mode)** + a throwaway script proving the official MCP Python SDK can call it and get real evidence back. Isolated, parallelizable with step 5, but must land before Agent K's investigation logic can be written against real data rather than mocks.
7. **Agent K skeleton: webhook receiver + state machine shell + MCP client wrapper**, wired to steps 5+6, producing a bare unstructured report. Proves the full alert→evidence loop end to end before adding safety/action complexity on top.
8. **Law 1 (evidence schema + link checker) and hybrid confidence scoring**, since Law 2's policy module needs a stable evidence/confidence shape to gate on — this is a hard dependency, not parallel work.
9. **Law 2 policy module + rollback executor**, unit-tested against synthetic evidence before wiring to the real docker-compose mutation; this is also where the "one team member unavailable July 24-26" constraint bites hardest, so front-load design of the policy schema before that gap.
10. **Law 3 self-telemetry, loop breaker, cost watchdog** — layered onto the now-working state machine; can be built incrementally alongside step 9 since both are cross-cutting wrappers around the same call sites (MCP client, LLM client).
11. **HTML report page + polished SigNoz dashboard (agent health, action audit trail sections) + evaluation harness (3 runs/incident)** — last, since both consume artifacts (reports, telemetry) that only exist once steps 1-10 are working.
12. **Submission blog**, written from the actual build log — genuinely last, depends on everything else being true.

**Critical path note:** steps 1-3 (telemetry → SigNoz → RAG app) are strictly sequential and are the highest-risk items given zero prior OTel/Docker experience — budget the largest ramp-up buffer here, not later. Steps 5 and 6 can run in parallel (different people/streams) once step 2 is done. Steps 8 and part of 9 (policy module design, independent of the actual docker mutation) can also be drafted before step 7 finishes, since the evidence/policy schema is really a data-contract decision that doesn't require a working state machine to write down.

## Sources

- [SigNoz MCP Server — GitHub](https://github.com/SigNoz/signoz-mcp-server) (MEDIUM — cross-verified against docs page below)
- [SigNoz MCP Server — AI Assistant Integration Guide](https://signoz.io/docs/ai/signoz-mcp-server/) (MEDIUM — cross-verified against GitHub README)
- [Model Context Protocol Python SDK — GitHub](https://github.com/modelcontextprotocol/python-sdk) (LOW — single-source WebSearch synthesis, verify exact API against installed SDK version at build time)
- [Implementing OpenTelemetry in FastAPI — SigNoz blog](https://signoz.io/blog/opentelemetry-fastapi/) (LOW — single-source synthesis)
- [OpenTelemetry GenAI Semantic Conventions overview](https://opentelemetry.io/blog/2026/genai-observability/) and related community writeups (LOW — single-source synthesis, verify current attribute names against `opentelemetry-semantic-conventions` package at build time since GenAI semconv is still evolving)
- [Configure Webhook Channel — SigNoz Docs](https://signoz.io/docs/alerts-management/notification-channel/webhook/) (LOW — single-source; verify exact payload shape and default grouping interval against the installed SigNoz version)
- Docker Compose rollback community discussions (Kristof Kovacs blog, Docker Community Forums) (LOW — no authoritative single source; expect to hand-roll the subprocess/YAML-edit implementation)
- LLM agent guardrail literature (AgentSpec, ShieldAgent, and related 2026 papers) (LOW — academic literature synthesis, used only to confirm the Law 2 design matches converging field practice, not as an implementation reference)

---
*Architecture research for: code-enforced incident-response agent + monitored RAG service*
*Researched: 2026-07-20*
