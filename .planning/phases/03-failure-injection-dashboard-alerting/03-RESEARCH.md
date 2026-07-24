# Phase 3: Failure Injection + Dashboard + Alerting - Research

**Researched:** 2026-07-24
**Domain:** SigNoz self-hosted (Foundry) deployment markers, alerting/webhooks, dashboard export, and in-process fault injection on top of the existing FastAPI RAG service
**Confidence:** MEDIUM (SigNoz's official docs are thin on internals for deployment markers and SLO/burn-rate mechanics; codebase-facing findings are HIGH — verified by direct file reads)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Feature-flag service (FLAG-01)**
- Single admin endpoint + token. `POST /admin/flags` accepts JSON `{name, enabled}`;
  `GET /admin/flags` returns the current state of all four flags. State lives in an in-memory
  module-level store (dict), read **fresh per request** at each injection point — no restart to
  toggle (FLAG-01), no persistence across restart (matches spec's in-memory intent).
- **Auth:** guarded by a shared-secret `X-Admin-Token` header sourced from env. If the env var is
  **empty/unset, the endpoint is open** — deliberate so the local demo/eval harness works without
  ceremony. When set, a mismatch returns 401.
- **Registration order:** admin routes MUST be registered before `FASTAPIInstrumentor.instrument_app(app)`
  in `app/main.py`, same as `/ask` — anything registered after that call is never wrapped in spans.

**Deployment markers (FLAG-06)**
- **SigNoz API call on toggle.** When a *deployment-class* scenario (prompt-regression, retry-storm)
  is toggled **on**, the app makes an explicit call to SigNoz to create a deployment / change-event
  marker so it appears live in the dashboard's Incident Context. The two *non-deployment* scenarios
  (retrieval-latency, DB-pool-exhaustion) deliberately skip this call — that asymmetry is the whole
  point of FLAG-06 and Success Criterion 2.
- **Rejected:** encoding the version in the OTel resource and bumping it per scenario. The OTel
  resource is fixed at process start, so a live flag toggle can't change it without a restart —
  directly conflicts with FLAG-01's no-restart requirement.
- **For the researcher:** confirm the exact SigNoz mechanism/endpoint/payload for creating a
  deployment or change-event marker in the self-hosted (Foundry) build. **This is the
  highest-uncertainty item in the phase — see "Key Finding 1" below: no such native API exists.**

**Alert webhook receiver (DASH-05)**
- **Reusable Agent K stub, not a throwaway.** Build a real `POST /alerts/webhook` entrypoint in its
  own module that validates, logs, and persists the incoming SigNoz alert payload. It is designed to
  be the actual trigger Agent K's Phase 5 investigation loop consumes.
- Must be reachable by the SigNoz alertmanager over the compose network. Payload shape and
  persistence format (alert name, severity, start time, affected service, related trace/label
  context) are for the researcher/planner to pin against SigNoz's actual webhook payload.

**Manual-UI vs code split (DASH-01/02/05)**
- **Code now; SigNoz UI work captured as a runbook.** All codeable work — flag service, the four
  fault injectors, the deployment-marker emitter, the webhook receiver, and their tests — is built
  and verified in this phase without requiring a live SigNoz stack.
- The hand-built deliverables (Service Health + Incident Context dashboard sections, SLO/burn-rate/
  cost alert rules) are captured as **documented human-action steps** appended to
  SIGNOZ-RUNBOOK.md, and the **exported dashboard/alert JSON is committed into the repo** (DASH-01
  requires this) once the stack is live.
- The phase is **not blocked** on HV-2 (live SigNoz). Human-action items and the JSON-export step
  are tracked as pending verification, mirroring how Phase 2 handled HV-1/HV-2.

### Claude's Discretion
- Exact metric/attribute names for new fault-injection telemetry (must live in `app/observability.py`
  per D-06, not be inline string literals).
- Exact shape of the in-memory flag dict, its accessor functions, and how each of the four
  injection points reads it fresh per call.
- Exact persistence format for the webhook receiver's stored alert records (file, in-memory list,
  or lightweight table) — DASH-05 only requires validate/log/persist, not a specific store.
- Whether the deployment-marker emission is a span, a log record, or a metric — CONTEXT.md leaves
  the *mechanism* open, only pins the *timing* (on toggle-on, scenarios 1-2 only) and the *intent*
  (must show up in the dashboard's Incident Context, distinguishable from non-deployment toggles).

### Deferred Ideas (OUT OF SCOPE)
- **DASH-03 (Agent Health) and DASH-04 (Action Audit Trail)** dashboard sections — deferred to
  Phase 7 (their data doesn't exist until Agent K / Law 2 are built). Not in this phase.
- Dashboard-as-code / programmatic alert provisioning (SigNoz's own AI agent-skills / Terraform
  provider) — explicitly out of scope per PROJECT.md; dashboard/alerts are hand-built in the UI.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLAG-01 | In-process feature-flag service, HTTP-toggleable, no restart | See "Architecture Patterns" Pattern 1 (flag store) and Pattern 2 (route-before-instrumentation, already established in `app/main.py`) |
| FLAG-02 | Prompt-regression scenario: broken prompt, rising failed-answer rate, **has** deployment marker | See "Code Examples: Fault Injector 1" and Pitfall "Unobservable prompt regression" |
| FLAG-03 | Retry-storm scenario: lowered timeouts, repeated LLM calls, cost/call-rate spike, error rate not necessarily up | See "Code Examples: Fault Injector 2" and "Don't Hand-Roll" retry row |
| FLAG-04 | Retrieval-latency scenario: artificial delay in pgvector query, slow `rag.retrieval` spans, no deployment marker | See "Code Examples: Fault Injector 3" |
| FLAG-05 | DB-pool-exhaustion scenario: reduced connections, pool-exhaustion errors in logs correlated to failed traces, no deployment marker | See "Code Examples: Fault Injector 4" and Pitfall "Pool exhaustion needs concurrent load" |
| FLAG-06 | SigNoz deployment marker on every version change including flag-triggered ones, distinguishable from non-deployment toggles | See "Key Finding 1" (no native API — span-based marker), "Architecture Patterns" Pattern 3 |
| DASH-01 | Dashboard hand-built in SigNoz UI, exported as JSON, Service Health section | See "Key Finding 3" (export/import mechanics) and SIGNOZ-RUNBOOK.md addendum in "Code Examples" |
| DASH-02 | Dashboard Incident Context section (active alerts, deployment markers, incident start, affected service, trace IDs, links) | See "Key Finding 1" + "Architecture Patterns" Pattern 3 (marker query pattern for a panel) |
| DASH-05 | SLOs/burn-rate/cost alert rules hand-built, wired to a webhook | See "Key Finding 2" (webhook payload schema) and "Key Finding 4" (SLO/burn-rate has no first-party object — hand-computed threshold query) |
</phase_requirements>

## Summary

This phase has two very different halves. The **codeable half** (FLAG-01..06, the webhook stub)
is straightforward Python work layered on an already-well-established codebase pattern: a
module-level flag dict read fresh per call, four injection points that already exist as named
functions (`SYSTEM_PROMPT`/`build_prompt` in `app/rag.py`, `generate()` in `app/llm.py`,
`retrieve()` in `app/rag.py`, the engine construction in `app/db.py`), and a new FastAPI route
module for the webhook receiver. All of this can be built and fully tested offline, exactly like
Phase 2's `/ask` work, using the same `in_memory_exporter` fixture and the same
`scripts/probe_ask_spans.py`-style production-span-probe pattern.

The **SigNoz half** is where this phase's real uncertainty lives, and the CONTEXT.md-flagged "top
research item" resolves to a negative finding: **SigNoz has no native deployment-marker,
change-event, or dashboard-annotation API.** A community feature request for exactly this
(`SigNoz/signoz#6162`, "Ability to add annotations to panels in dashboards. Eg, deployment
markers") exists and is closed without documented first-party support landing; SigNoz's own
"post-deployment monitoring" AI use-case doc works around the gap by having a human/agent manually
note a deployment **timestamp** and compare metrics before/after it — it does not call any marker
API. This means FLAG-06's "explicit SigNoz API call" must be reinterpreted as **emitting a custom
OTel span** (reusing the project's existing OTLP pipeline, no new package, no new endpoint) rather
than calling a SigNoz-specific REST endpoint. This is consistent with — and should reuse the same
convention as — the deployment-marker approach already locked in PROJECT.md's Key Decisions table
for the Phase 6 deployer sidecar (`deployment.marker` custom span). Dashboard Incident Context then
surfaces markers via a Trace/Logs Explorer panel filtered on that span name, not via a native
timeline-annotation overlay.

The webhook and dashboard-export mechanics are both well-documented and low-risk: SigNoz's webhook
channel POSTs an Alertmanager-shaped JSON body (`receiver`, `status`, `alerts[]` with
`labels`/`annotations`/`startsAt`/`endsAt`/`fingerprint`, `groupLabels`, `commonLabels`,
`commonAnnotations`, `externalURL`, `version`, `groupKey`), grouped by alert name on a 5-minute
window by default. Dashboard export/import is a manual UI action (Dashboard menu → copy/download
JSON; new dashboard → Import JSON), with a V2 dashboards API (`GET/POST/PUT/PATCH
/api/v2/dashboards`) available as a scriptable alternative to committing the same JSON, though the
locked decision is to hand-build via UI and only use the API (if at all) to fetch the JSON that was
already hand-built for committing to the repo.

**Primary recommendation:** build all four fault injectors and the flag/webhook code now, fully
tested offline; emit deployment markers as a custom `deployment.marker` OTel span (not a SigNoz API
call) gated by the flag-class asymmetry; and treat the dashboard/alert-rule construction, the
SLO/burn-rate query, and the live webhook-fire confirmation as SIGNOZ-RUNBOOK.md human-action steps
gated on HV-2, exactly as CONTEXT.md's manual-UI-vs-code split already anticipates.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Feature-flag store + admin HTTP toggle | API / Backend (`app/main.py`, new `app/flags.py`) | — | In-process module-level state, read by request handlers; no separate service per locked decision |
| Prompt-regression injector | API / Backend (`app/rag.py`) | — | Swaps a module-level string read inside `build_prompt()`; pure application logic |
| Retry-storm injector | API / Backend (`app/llm.py`) | — | Wraps the existing `generate()` call site with a retry/timeout loop, no new external dependency |
| Retrieval-latency injector | API / Backend (`app/rag.py`) | Database / Storage | Injected delay lives in the app before/around the pgvector query; the query itself still executes against Postgres |
| DB-pool-exhaustion injector | API / Backend (`app/db.py`) | Database / Storage | Pool sizing is an SQLAlchemy engine config concern in the app tier; symptoms surface as Postgres/asyncpg connection errors |
| Deployment marker emission | API / Backend (custom OTel span in the FastAPI process) | Observability backend (SigNoz Trace Explorer/query) | No native SigNoz API exists (Key Finding 1); the "marker" is application-emitted telemetry, consumed by SigNoz's existing query engine, not a dedicated marker service |
| Alert webhook receipt | API / Backend (new `app/alerts_webhook.py`, own route module) | — | A plain FastAPI POST handler; validation/logging/persistence stays in-process per DASH-05's "own module" decision |
| Dashboard (Service Health / Incident Context) | Observability backend (SigNoz UI) | — | Entirely SigNoz-side configuration; hand-built per locked decision, exported as JSON artifact |
| SLO/burn-rate/cost alert rules | Observability backend (SigNoz UI) | API / Backend (webhook target) | Rule definition lives in SigNoz; the webhook target it fires into is the API-tier receiver above |

## Standard Stack

### Core

No new core libraries are required for this phase. All four fault injectors, the flag service, and
the webhook receiver are buildable with packages already pinned in `requirements.txt`
`[VERIFIED: requirements.txt]`:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.139.2 (pinned) | New `/admin/flags`, `/alerts/webhook` routes | Already the project's web framework; new routes follow the exact registration-order pattern `app/main.py` establishes `[VERIFIED: app/main.py]` |
| `opentelemetry-sdk`/`opentelemetry-api` | 1.44.0 (pinned) | Custom `deployment.marker` span/metric, fault-injection span attributes | `MeterProvider` and `TracerProvider` are already wired in `app/telemetry.py`; no new exporter or provider needed `[VERIFIED: app/telemetry.py]` |
| `pydantic` | 2.13.4 (transitively pinned via FastAPI) | Webhook payload schema, `/admin/flags` request/response models | Already the project's validation library `[VERIFIED: requirements.txt via FastAPI dependency]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` (already in requirements.txt) | latest | Optional: a smoke-test script `curl`-equivalent to POST fault-injection flags and the webhook during manual verification | Only if the planner wants a Python smoke-test script instead of raw `curl`/PowerShell `Invoke-RestMethod` calls in SIGNOZ-RUNBOOK.md |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `deployment.marker` OTel span for FLAG-06 | A SigNoz-native deployment-marker/annotation API | **Not available** — `[CITED: github.com/SigNoz/signoz/issues/6162]` confirms this was requested and is closed without first-party support; do not plan around an API that doesn't exist |
| Hand-built webhook Pydantic schema matching Alertmanager shape | Reusing a third-party Alertmanager-webhook parsing library | Unnecessary dependency for a ~6-field JSON body; hand-rolling the schema is simpler and keeps validation logic auditable for Law 1 evidence-schema reuse later |
| In-memory module-level flag dict | Redis/external flag store (e.g., a lightweight feature-flag SaaS/service) | Explicitly rejected by CONTEXT.md/locked decisions — in-memory-only is the spec's stated intent, and any external store would violate the zero-budget/single-datastore constraints |

**Installation:** none — no new packages needed for this phase's codeable half.

**Version verification:** all versions above were read directly from the committed
`requirements.txt`, not re-queried against PyPI, since no new packages are introduced.

## Package Legitimacy Audit

**Not applicable this phase** — no new external packages are installed. All fault-injection,
flag-service, and webhook-receiver code is built from packages already present in
`requirements.txt` (verified above). If a future gap-closure plan introduces a package (e.g., a
retry-backoff library for the retry-storm injector), run the full Package Legitimacy Gate at that
time; `tenacity` is flagged in CLAUDE.md as `[LOW — architectural judgment call]` and is
deliberately **not** recommended here (see "Don't Hand-Roll" below — the retry loop for the
retry-storm *scenario* should be hand-rolled precisely so each retry is independently visible as a
span, which a library like `tenacity` would either hide or require extra wiring to expose).

## Architecture Patterns

### System Architecture Diagram

```
Admin/operator
     |
     | POST /admin/flags {name, enabled}  (X-Admin-Token header)
     v
+-------------------------+
|  app/flags.py           |   in-memory dict, read fresh per call
|  {name: bool}           |
+-------------------------+
     ^        ^        ^        ^
     | read   | read   | read   | read (fresh, per request)
     |        |        |        |
+----+---+ +--+-----+ +-+------+ +-+--------+
| rag.py | | llm.py | | rag.py | | db.py    |
| prompt | | retry  | | delay  | | pool     |
| swap   | | storm  | | inject | | shrink   |
+----+---+ +--+-----+ +-+------+ +-+--------+
     |        |          |          |
     v        v          v          v
  POST /ask  (FastAPI, routes registered BEFORE FastAPIInstrumentor.instrument_app)
     |
     v
+----------------------------------------------------+
| OTel SDK (app/telemetry.py) - Tracer/Meter/Logger   |
| dual-export: console + OTLP-HTTP :4318              |
+----------------------------------------------------+
     |
     v
SigNoz OTel Collector -> ClickHouse -> Query Service -> SigNoz UI
     |                                        |
     |  (deployment.marker span, scenarios    |  Dashboard (Service Health,
     |   1-2 only, emitted same path as       |  Incident Context) - hand-built,
     |   any other span - no separate API)    |  exported JSON committed to repo
     v                                        v
Alert rule (metric/log threshold, burn-rate query) evaluated by SigNoz Alertmanager
     |
     | webhook_configs[].url  (POST, Alertmanager-shaped JSON body)
     v
+---------------------------+
| app/alerts_webhook.py     |
| POST /alerts/webhook      |
| validate -> log -> persist|
+---------------------------+
     |
     v
(Phase 5: Agent K investigation loop consumes persisted alert records)
```

### Recommended Project Structure

```
app/
├── flags.py               # NEW: in-memory flag store + accessor functions
├── alerts_webhook.py       # NEW: POST /alerts/webhook, own module per DASH-05
├── observability.py         # EXTEND: new attribute/metric-name constants for fault injectors + markers
├── main.py                 # EXTEND: register /admin/flags and /alerts/webhook routes BEFORE instrument_app()
├── rag.py                  # EXTEND: build_prompt() reads flag for prompt swap; retrieve() reads flag for delay
├── llm.py                  # EXTEND: generate() reads flag for retry-storm behavior
└── db.py                   # EXTEND: engine pool-size reads flag/env at construction OR a rebuild-on-toggle path (see Pitfall)
tests/
├── test_flags.py           # NEW: admin endpoint auth, toggle, fresh-read semantics
├── test_fault_injection.py # NEW: one test class per scenario, proving the injected symptom via in_memory_exporter/metrics
└── test_alerts_webhook.py  # NEW: payload validation, persistence, malformed-payload handling
SIGNOZ-RUNBOOK.md            # EXTEND: dashboard build steps, alert rule build steps, JSON export steps, webhook-fire confirmation steps
.planning/phases/03-.../     # dashboard.json / alerts.json committed here or under a top-level dashboards/ dir once hand-built
```

### Pattern 1: Fresh-per-request flag store

**What:** A module-level dict (`_flags: dict[str, bool]`) with `is_enabled(name)` /
`set_flag(name, enabled)` functions. No caching, no request-scoped copy — every injection point
calls `is_enabled(...)` directly inside the function body, mirroring the project's own
"fresh-per-call tracer" convention already documented in `app/rag.py`'s module docstring.

**When to use:** Every one of the four injection points, plus the `/admin/flags` GET handler.

**Example:**
```python
# app/flags.py
FLAG_NAMES = (
    "prompt_regression",
    "retry_storm",
    "retrieval_latency",
    "db_pool_exhaustion",
)

_flags: dict[str, bool] = {name: False for name in FLAG_NAMES}


def is_enabled(name: str) -> bool:
    """Read current state fresh - no caching, mirrors the fresh-per-call
    tracer pattern already used by app/rag.py and app/llm.py."""
    return _flags.get(name, False)


def set_flag(name: str, enabled: bool) -> None:
    if name not in _flags:
        raise KeyError(f"unknown flag {name!r}; must be one of {FLAG_NAMES}")
    _flags[name] = enabled
```

### Pattern 2: Route-before-instrumentation (already established)

**What:** `app/main.py` registers all routes, THEN calls `setup_telemetry()`, THEN
`FastAPIInstrumentor.instrument_app(app)`. `/admin/flags` and `/alerts/webhook` must be added in
the routes-registration block (step 2 in the existing numbered comments), not appended after step 4.

**When to use:** Any new route added in this phase.

**Example:** (already the pattern in `app/main.py`, extend in place)
```python
# app/main.py - step 2 region
@app.post("/admin/flags")
async def set_flags(req: FlagToggleRequest, x_admin_token: str | None = Header(default=None)):
    _check_admin_token(x_admin_token)
    flags.set_flag(req.name, req.enabled)
    return {"flags": flags.get_all()}

@app.get("/admin/flags")
async def get_flags():
    return {"flags": flags.get_all()}

app.include_router(alerts_webhook.router)  # POST /alerts/webhook, own module

# ... later, unchanged:
setup_telemetry()
FastAPIInstrumentor.instrument_app(app)
```

### Pattern 3: Deployment marker as a custom span (not a SigNoz API call)

**What:** Since no native SigNoz deployment-marker API exists (Key Finding 1), emit a short-lived
span named `deployment.marker` through the app's already-configured `TracerProvider`, carrying
attributes that make it queryable and Law-1-evidence-linkable later: service name (already in the
Resource), a `deployment.scenario` attribute, and a `deployment.version`/timestamp attribute. Only
call this from the `set_flags()` handler when the toggled flag is `prompt_regression` or
`retry_storm` AND `enabled=True` — this is the FLAG-06 asymmetry.

**When to use:** Inside `/admin/flags`'s POST handler, immediately after `flags.set_flag(...)`.

**Example:**
```python
# app/flags.py or app/main.py - called from the POST /admin/flags handler
from opentelemetry import trace
from app.observability import DEPLOYMENT_MARKER_SCENARIO, DEPLOYMENT_MARKER_VERSION

DEPLOYMENT_CLASS_FLAGS = {"prompt_regression", "retry_storm"}

def maybe_emit_deployment_marker(flag_name: str, enabled: bool) -> None:
    if enabled and flag_name in DEPLOYMENT_CLASS_FLAGS:
        tracer = trace.get_tracer(__name__)  # fresh per-call, same convention as rag.py/llm.py
        with tracer.start_as_current_span("deployment.marker") as span:
            span.set_attribute(DEPLOYMENT_MARKER_SCENARIO, flag_name)
            span.set_attribute(DEPLOYMENT_MARKER_VERSION, f"flag-toggle-{flag_name}")
```
The dashboard's Incident Context section then uses a Trace Explorer / logs panel filtered on
`name = "deployment.marker"` (SigNoz Query Builder, trace search by span name) to list recent
markers — this is a hand-built panel, not a native annotation overlay line, because SigNoz has no
overlay primitive for this (see Key Finding 1).

### Anti-Patterns to Avoid
- **Bumping `OTEL_SERVICE_NAME`/resource version per scenario toggle:** rejected in CONTEXT.md —
  the `Resource` is fixed at `TracerProvider` construction time (process start); a live toggle
  cannot change it without a restart, which directly breaks FLAG-01's no-restart requirement.
- **Adding a new route after `FastAPIInstrumentor.instrument_app(app)`:** breaks tracing for that
  route entirely — this is a documented anti-pattern already called out in `app/main.py`'s
  docstring; the same rule applies to `/admin/flags` and `/alerts/webhook`.
- **Caching the flag dict read at import time or once per process:** defeats FLAG-01's no-restart
  requirement — always read `is_enabled(name)` at the point of use, inside the function body.
- **Assuming a SigNoz deployment-marker REST endpoint exists and building retry/backoff logic
  around calling it:** it does not exist (Key Finding 1) — don't spend planning budget designing
  error handling for a call that was never real.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alertmanager-webhook JSON parsing | A generic/flexible parser for arbitrary alerting-tool payload shapes | A narrow Pydantic model matching exactly the fields SigNoz's webhook doc documents (`receiver`, `status`, `alerts[]`, `groupLabels`, `commonLabels`, `commonAnnotations`, `externalURL`, `version`, `groupKey`) | SigNoz only ever sends this one shape; over-generalizing adds untested surface area for a 7-day build |
| Deployment-marker delivery reliability | Retry/backoff around a (nonexistent) SigNoz marker API call | A same-process OTel span through the already-batched/retrying `BatchSpanProcessor` + OTLP exporter pipeline | The OTel SDK's batch processor already handles export retries/buffering; there is no separate API call to retry around once you use the span-based approach |
| Admin-token comparison | A plain `==` string comparison for `X-Admin-Token` | `hmac.compare_digest()` | Constant-time comparison avoids a (low-severity but free-to-fix) timing side-channel on the shared secret; trivial to add, listed under Security Domain below |

**Key insight:** every "don't hand-roll" item in this phase is really about not over-engineering
around SigNoz capabilities that don't exist (retrying a marker API) or over-generalizing a payload
shape that is fixed and documented (the webhook body) — the actual net-new code surface this phase
needs is small and should stay small.

## Common Pitfalls

### Pitfall 1: Assuming a SigNoz deployment-marker API exists
**What goes wrong:** Time is spent hunting for (or worse, building error-handling around) a
`POST /api/v1/deployments` or `/api/v1/annotations`-style endpoint that CONTEXT.md's phrasing
("makes an explicit call to SigNoz to create a deployment / change-event marker") implies exists.
**Why it happens:** Other observability vendors (Datadog, Grafana, Honeycomb) do have first-party
deployment-marker/annotation APIs, so the assumption is reasonable but wrong for SigNoz specifically.
**How to avoid:** Use the span-based marker pattern (Pattern 3 above) instead — it satisfies the
same intent (a queryable, timestamped, evidence-linkable record of "a deployment-class scenario
just turned on") without a nonexistent API.
**Warning signs:** Any task description phrased as "call the SigNoz deployment-marker endpoint" —
rewrite to "emit a `deployment.marker` span."

### Pitfall 2: Unobservable prompt regression (FLAG-02)
**What goes wrong:** Swapping `SYSTEM_PROMPT` for a broken variant changes *answer quality*, but
nothing in the existing trace/metric set directly measures "answer quality" or "failed-answer
rate" — the `/ask` endpoint still returns HTTP 200 with *some* string. Without a new signal, the
"rising failed-answer rate" success criterion has nothing concrete to point at in SigNoz.
**Why it happens:** The existing three GenAI spans (`rag.retrieval`, `rag.prompt_construction`,
`chat`) record token counts and doc counts, not answer correctness.
**How to avoid:** Add an explicit, cheap signal: a boolean/gauge metric or span attribute (e.g.
`rag.prompt_construction.regression_active` on the existing `rag.prompt_construction` span, plus
an OTel counter `agentk.flag.enabled{flag_name="prompt_regression"}`) that is unambiguously true
whenever the flag is on. Pair this with the dashboard panel filtering on that attribute/metric so
"rising failed-answer rate" is demonstrable as "regression-flag-active requests coincide with a
human-judged answer-quality drop during the demo," not something SigNoz infers on its own.
**Warning signs:** Planner writes a task whose verification step is "check the answer looks worse"
with no corresponding metric/attribute to query in SigNoz — flag this as needing the new signal.

### Pitfall 3: DB-pool-exhaustion needs concurrent load to manifest (FLAG-05)
**What goes wrong:** Reducing `pool_size`/`max_overflow` in `app/db.py` only produces
connection-pool-exhaustion errors under **concurrent** requests exceeding the (now small) pool —
a single sequential `curl /ask` will never exhaust a pool of size 1-2 on its own.
**Why it happens:** SQLAlchemy's async pool only blocks/raises `TimeoutError` when more concurrent
checkouts are requested than the pool + overflow allow.
**How to avoid:** The fault-injection test/demo for this scenario must issue several concurrent
`/ask` requests (e.g., `asyncio.gather` of N `httpx.AsyncClient` calls, or a small locust/ab-style
script) against a pool sized down to 1 with `max_overflow=0`. Document this concurrency requirement
explicitly in the task's verification steps, not just "reduce the pool size."
**Warning signs:** A verification step that only does one sequential request and expects to see a
pool-exhaustion error.

### Pitfall 4: Pool size is normally fixed at engine-construction time
**What goes wrong:** `app/db.py`'s `_engine = create_async_engine(_database_url)` runs once at
import time; `pool_size`/`max_overflow` are constructor kwargs, not something re-readable per
request like the other three flags.
**Why it happens:** SQLAlchemy engines don't expose a live pool-resize API comparable to a simple
dict read.
**How to avoid:** Two viable approaches — (a) parameterize `create_async_engine(..., pool_size=1,
max_overflow=0)` behind a **startup-time** env var/flag read (accepting that this one scenario,
unlike the other three, needs a process restart or a pre-configured tiny pool that's toggled via a
different mechanism — e.g., an app-level semaphore in `get_session()` that artificially limits
concurrent checkouts when the flag is on, without touching the real SQLAlchemy pool); or (b) build
a small application-level connection-limiting wrapper around `get_session()` that raises the same
class of error (`TimeoutError`/pool-exhaustion-shaped exception) when the flag is enabled and N
concurrent sessions are already open — this keeps FLAG-05 toggleable live like the other three
without touching engine construction. **Recommend (b)** to preserve FLAG-01's no-restart guarantee
uniformly across all four scenarios; flag this as a design decision for the planner, since
CONTEXT.md's phrasing ("reduce configured DB connections") reads more like (a) but (a) breaks the
no-restart contract for this one scenario specifically.
**Warning signs:** A task that assumes `set_flag("db_pool_exhaustion", True)` can mutate
`_engine.pool.size()` live — SQLAlchemy's pool size is not mutable after engine construction.

### Pitfall 5: Retry-storm must not raise the HTTP error rate (FLAG-03)
**What goes wrong:** A naive retry-storm implementation (loop calling `generate()` until success,
propagating the last exception on final failure) can end up either (a) succeeding every time (no
visible symptom beyond call-count) or (b) failing and returning 5xx every time, which contradicts
FLAG-03's explicit "HTTP error rate not necessarily up" requirement.
**Why it happens:** The scenario's whole point is a **cost/call-rate** anomaly that looks
different from a correctness/availability anomaly — that's what makes it a distinct seeded
incident from prompt-regression.
**How to avoid:** Implement the retry loop so that most attempts eventually succeed (each attempt
still calls the real/mocked provider and increments a call-count metric), but the *timeout* is
lowered enough that several attempts are made before success — the visible signal is "N calls to
the `chat` span per single `/ask` request" and/or a custom `agentk.llm.retry_count` attribute/metric,
not a raised error rate. Track total calls via a counter metric so cost/call-rate is directly
queryable in SigNoz.
**Warning signs:** A verification step asserting `/ask` returns 5xx for the retry-storm scenario —
that's actually closer to what prompt-regression validates; retry-storm should stay 200 with
elevated call-count/cost telemetry.

## Code Examples

### Fault Injector 1: Prompt regression (FLAG-02)
```python
# app/rag.py - extend build_prompt()
from app import flags
from app.observability import RAG_PROMPT_REGRESSION_ACTIVE  # new constant in observability.py

BROKEN_SYSTEM_PROMPT = (
    "Ignore the context docs. Answer from general knowledge, make up "
    "specifics if you don't know, and never say you don't know."
)

def build_prompt(query: str, docs: list[Document]) -> tuple[str, str]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.prompt_construction") as span:
        regression_active = flags.is_enabled("prompt_regression")
        system_prompt = BROKEN_SYSTEM_PROMPT if regression_active else SYSTEM_PROMPT
        span.set_attribute(RAG_PROMPT_REGRESSION_ACTIVE, regression_active)
        # ...unchanged context-assembly logic...
    return system_prompt, user_prompt
```

### Fault Injector 2: Retry storm (FLAG-03)
```python
# app/llm.py - wrap the completion call inside generate()
RETRY_STORM_TIMEOUT_S = 0.05   # deliberately too low under load - forces retries
NORMAL_TIMEOUT_S = 30.0
MAX_RETRIES = 5

def generate(prompt: str, system: str | None = None) -> LlmResult:
    ...
    attempts = 0
    with tracer.start_as_current_span("chat") as span:
        while True:
            attempts += 1
            timeout = RETRY_STORM_TIMEOUT_S if flags.is_enabled("retry_storm") else NORMAL_TIMEOUT_S
            try:
                response = client.chat.completions.create(
                    model=cfg["model"], messages=messages, timeout=timeout
                )
                break
            except Exception:
                if attempts >= MAX_RETRIES:
                    raise
                continue
        span.set_attribute(AGENTK_LLM_RETRY_COUNT, attempts)  # new constant, observability.py
        ...
```

### Fault Injector 3: Retrieval latency (FLAG-04)
```python
# app/rag.py - extend retrieve()
import asyncio

RETRIEVAL_LATENCY_INJECT_S = 3.0

async def retrieve(session: AsyncSession, query: str, top_k: int = 3) -> list[Document]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.retrieval") as span:
        if flags.is_enabled("retrieval_latency"):
            span.set_attribute(RAG_RETRIEVAL_LATENCY_INJECTED, True)
            await asyncio.sleep(RETRIEVAL_LATENCY_INJECT_S)
        query_vector = embed_text(query)
        ...  # unchanged
```

### Fault Injector 4: DB-pool exhaustion (FLAG-05) — application-level limiter (Pitfall 4, option b)
```python
# app/db.py - extend get_session() with a live-toggleable concurrency cap
import asyncio
from app import flags

_pool_exhaustion_semaphore = asyncio.Semaphore(1)  # simulates pool_size=1 when flag is on

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if flags.is_enabled("db_pool_exhaustion"):
        try:
            await asyncio.wait_for(_pool_exhaustion_semaphore.acquire(), timeout=0.5)
        except asyncio.TimeoutError as exc:
            logging.getLogger(__name__).error("db pool exhaustion: no connection slot available")
            raise TimeoutError("simulated DB pool exhaustion") from exc
        try:
            async with AsyncSessionLocal() as session:
                yield session
        finally:
            _pool_exhaustion_semaphore.release()
    else:
        async with AsyncSessionLocal() as session:
            yield session
```

### Webhook receiver schema (DASH-05)
```python
# app/alerts_webhook.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AlertItem(BaseModel):
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: str
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None

class AlertmanagerWebhookPayload(BaseModel):
    receiver: str
    status: str
    alerts: list[AlertItem]
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str | None = None
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = None

@router.post("/alerts/webhook")
async def receive_alert(payload: AlertmanagerWebhookPayload):
    # validate (Pydantic already did this) -> log -> persist
    for alert in payload.alerts:
        logging.getLogger(__name__).info(
            "alert received: %s status=%s", payload.groupLabels.get("alertname"), alert.status
        )
        _persist_alert(payload.receiver, alert)  # in-memory list or lightweight table - planner's discretion
    return {"received": len(payload.alerts)}
```
Source basis for the payload shape: `[CITED: signoz.io/docs/alerts-management/notification-channel/webhook/]`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| SigNoz's plain `docker-compose.yaml` distribution | Foundry (`foundryctl gauge/forge/cast`) | as of SigNoz v0.130.0 (per SIGNOZ-RUNBOOK.md, already incorporated) | Already accounted for in this repo's runbook — no action needed this phase |
| Dashboards V1 API | Dashboards V2 API (`/api/v2/dashboards`, JSON-Patch-style `PATCH`) | Documented as current in SigNoz docs at research time | If the planner wants a scripted "pull the hand-built dashboard JSON" step instead of a manual UI export, use the V2 `GET /api/v2/dashboards/{id}` endpoint |

**Deprecated/outdated:**
- Legacy SigNoz `docker-compose.yaml` install path — already superseded per SIGNOZ-RUNBOOK.md;
  not relevant to re-litigate this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SigNoz has no native deployment-marker/annotation API and the closed GitHub issue #6162 reflects the current (unimplemented) state, not a since-shipped feature under a different name | Summary, Key Finding 1, Pattern 3 | If SigNoz has since shipped a marker API under a different name (e.g., via the newer AI agent-skills layer), the span-based workaround is unnecessarily complex — verify by checking the SigNoz changelog/agent-skills docs again at plan time before committing to the span approach |
| A2 | SigNoz has no first-party "SLO object" (unlike Datadog/Elastic) and burn-rate must be hand-computed as a threshold metric query | Summary, Phase Requirements DASH-05 row | If wrong, the runbook step for DASH-05 could be simpler (a native SLO wizard) than documented — low risk, just extra manual steps if the assumption is conservative |
| A3 | The webhook payload shape documented at signoz.io (Alertmanager-style `alerts[]`/`groupLabels`/etc.) is accurate for the current self-hosted Foundry-cast version, not a stale doc snapshot | Code Examples: webhook schema | If the live payload differs, `app/alerts_webhook.py`'s Pydantic model will reject real alerts with 422 at verification time — HV-2 (live SigNoz stack) is the natural point to confirm this; the Pydantic model should be treated as provisional until then |
| A4 | Application-level semaphore limiter (Pitfall 4, option b) is an acceptable stand-in for "reduce configured DB connections" and will still visibly correlate errors with failed traces in SigNoz the way a real pool-exhaustion would | Pitfall 4, Fault Injector 4 | If a judge/reviewer expects the literal SQLAlchemy pool size to shrink, this is a semantic gap — flag for the planner to confirm this interpretation matches FLAG-05's intent before implementing |

**If this table is empty:** N/A — see rows above; all four should be confirmed or explicitly
accepted by the planner/user before or during planning.

## Open Questions

1. **Exact mechanism for FLAG-05 given SQLAlchemy's fixed-at-construction pool size**
   - What we know: `create_async_engine()` sets `pool_size`/`max_overflow` once, at import time in
     `app/db.py`; there's no supported live-resize API.
   - What's unclear: whether the planner should (a) accept a startup-time-only pool size (breaking
     FLAG-01's no-restart uniformity for this one scenario) or (b) build an application-level
     concurrency limiter that mimics pool exhaustion without touching the real engine (Pitfall 4).
   - Recommendation: use (b) for consistency with the other three live-toggleable scenarios; note
     this in the plan as a deliberate design choice, not a literal "shrink the pool" implementation.

2. **How "rising failed-answer rate" (FLAG-02) is quantified without a real accuracy oracle**
   - What we know: no existing signal measures answer correctness; the three GenAI spans measure
     token/doc counts only.
   - What's unclear: whether the phase should add a genuine (if crude) answer-quality heuristic
     (e.g., detecting the model's own "I don't know" refusal rate drops when the broken prompt is
     active) or simply rely on a `regression_active` flag/attribute as the demoable signal, leaving
     "did the answer actually get worse" to human/demo judgment.
   - Recommendation: add the `regression_active` attribute (cheap, always correct) and treat actual
     answer-quality measurement as out of scope for Phase 3 (Phase 7's eval harness is the natural
     home for real accuracy scoring across seeded incidents).

3. **Whether the V2 Dashboards API should be used to script the "export JSON to repo" step**
   - What we know: SigNoz's V2 API supports `GET /api/v2/dashboards/{id}` for full JSON retrieval
     after the dashboard is hand-built in the UI.
   - What's unclear: whether using this API to fetch (not build) the JSON crosses the
     "dashboard-as-code" out-of-scope line from PROJECT.md, or whether it's acceptable since the
     dashboard itself was still hand-built.
   - Recommendation: treat API-based retrieval of an already-hand-built dashboard's JSON as
     in-scope (it's just "export," equivalent to the UI's copy/download button) and note this
     explicitly in SIGNOZ-RUNBOOK.md so a future reviewer doesn't misread it as programmatic
     provisioning.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Live SigNoz stack (Foundry-cast) | Dashboard build, alert rule build, webhook end-to-end fire (Success Criterion 4), FLAG-06 marker query verification | ✗ (not verified in this research session — HV-2 still open per STATE.md) | — | All codeable work (flags, injectors, webhook receiver) is fully testable offline via `in_memory_exporter`/mocks; SigNoz-dependent verification steps are deferred to HV-2, matching Phase 2's precedent |
| Docker Desktop / Compose v2 | Running the live stack for HV-2 | Unknown in this environment | — | Same as above — not a blocker for this phase's codeable deliverables |
| Groq/Cerebras/Gemini API key | Only indirectly (retry-storm and prompt-regression injectors still call `generate()`) | Unknown (per STATE.md, RAG-04 needs-human-verification for real credentials) | — | Tests use the existing `mock_openai_client` fixture; live-provider exercise remains gated on HV-1, not new to this phase |

**Missing dependencies with no fallback:**
- None — the phase's success criteria that require a live SigNoz stack are explicitly deferred to
  documented human-action verification (HV-2), matching the locked manual-UI-vs-code split.

**Missing dependencies with fallback:**
- Live SigNoz stack — fallback is offline/mocked testing for all codeable work; SigNoz-side steps
  become SIGNOZ-RUNBOOK.md entries pending HV-2.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7+ (unpinned in requirements.txt) + pytest-asyncio |
| Config file | none dedicated — `tests/conftest.py` provides fixtures; no `pytest.ini`/`pyproject.toml` `[tool.pytest.ini_options]` block found; planner may want to add one for asyncio mode if not already implicit |
| Quick run command | `pytest tests/ -m "not integration" -q` |
| Full suite command | `pytest tests/ -q` (includes `integration`-marked tests requiring the live `rag-postgres` container per `tests/conftest.py`'s marker registration) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLAG-01 | `/admin/flags` toggles without restart, token-gated | unit (offline, TestClient) | `pytest tests/test_flags.py -q` | ❌ Wave 0 |
| FLAG-02 | Prompt swap changes `rag.prompt_construction` span attributes | unit (in_memory_exporter) | `pytest tests/test_fault_injection.py::test_prompt_regression -q` | ❌ Wave 0 |
| FLAG-03 | Retry loop increments call count, stays HTTP 200 | unit (mocked provider raising then succeeding) | `pytest tests/test_fault_injection.py::test_retry_storm -q` | ❌ Wave 0 |
| FLAG-04 | Injected delay measurable on `rag.retrieval` span duration | unit (in_memory_exporter, assert span duration/attribute) | `pytest tests/test_fault_injection.py::test_retrieval_latency -q` | ❌ Wave 0 |
| FLAG-05 | Concurrent requests exceeding limiter raise pool-exhaustion-shaped error | unit (asyncio.gather against the limiter) | `pytest tests/test_fault_injection.py::test_db_pool_exhaustion -q` | ❌ Wave 0 |
| FLAG-06 | `deployment.marker` span emitted only for prompt_regression/retry_storm toggle-on | unit (in_memory_exporter, assert span presence/absence per scenario) | `pytest tests/test_fault_injection.py::test_deployment_marker_asymmetry -q` | ❌ Wave 0 |
| DASH-05 | Webhook payload validated, logged, persisted; malformed payload rejected | unit (TestClient POST with valid/invalid Alertmanager-shaped JSON) | `pytest tests/test_alerts_webhook.py -q` | ❌ Wave 0 |
| DASH-01/DASH-02 | Dashboard sections show required metrics/markers | manual-only (SigNoz UI, HV-2-gated) | — (no automated command; SIGNOZ-RUNBOOK.md checklist) | N/A (manual) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -m "not integration" -q`
- **Per wave merge:** `pytest tests/ -q` (only meaningful once a live DB is available; otherwise
  same as quick run)
- **Phase gate:** Full suite green (offline portion) before `/gsd:verify-work`; SigNoz-dependent
  criteria (Success Criteria 2-4) verified separately against HV-2 per the manual-UI-vs-code split.

### Wave 0 Gaps
- [ ] `tests/test_flags.py` — covers FLAG-01
- [ ] `tests/test_fault_injection.py` — covers FLAG-02..06
- [ ] `tests/test_alerts_webhook.py` — covers DASH-05's code half
- [ ] No new fixtures needed beyond existing `in_memory_exporter`, `mock_openai_client`, `client`
      in `tests/conftest.py` — extend `conftest.py` only if a shared "reset all flags between
      tests" fixture is wanted (recommended, to avoid test-order-dependent flag leakage since the
      flag dict is module-level global state)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `X-Admin-Token` shared-secret header, compared with `hmac.compare_digest()` (not `==`) |
| V3 Session Management | no | No session state introduced — token is a static shared secret per request, not a session |
| V4 Access Control | yes | Admin routes (`/admin/flags`) gated by the token check; `/alerts/webhook` is intentionally open (SigNoz's own webhook config supports optional basic auth, but CONTEXT.md doesn't require it — flag as an open item for the planner if the webhook endpoint should also be token-gated) |
| V5 Input Validation | yes | Pydantic models for `/admin/flags` request body (flag name must be one of the four known names, `enabled` must be bool) and for the webhook payload (Alertmanager-shaped schema above) |
| V6 Cryptography | no | No cryptographic primitives beyond the constant-time token comparison; no secrets are generated or stored beyond the existing env-var pattern |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Timing attack on `X-Admin-Token` comparison | Information Disclosure | `hmac.compare_digest()` instead of `==` |
| Unauthenticated `/admin/flags` when env var unset (deliberate per CONTEXT.md) | Elevation of Privilege | Accepted risk for local demo/eval convenience — document explicitly in code comments and SIGNOZ-RUNBOOK.md that this must never be left unset in a reachable-beyond-localhost deployment |
| Unauthenticated `/alerts/webhook` receiving arbitrary POSTed JSON | Spoofing / Denial of Service | Strict Pydantic schema validation rejects malformed bodies (422) before any processing; consider documenting (not necessarily implementing, given zero-budget/7-day constraints) that SigNoz's optional basic-auth webhook config could be enabled to reduce spoofing risk — flag as planner's discretion, not a hard requirement from CONTEXT.md |
| Fault-injection flags left enabled after a demo (e.g., `db_pool_exhaustion` stuck on) | Denial of Service (self-inflicted) | `GET /admin/flags` lets an operator audit current state at any time; recommend the plan include an explicit "reset all flags to false" smoke-test step as part of any verification script |

## Sources

### Primary (HIGH confidence)
- `app/main.py`, `app/rag.py`, `app/llm.py`, `app/db.py`, `app/observability.py`, `app/schemas.py`,
  `app/telemetry.py`, `tests/conftest.py`, `tests/test_ask.py`, `scripts/probe_ask_spans.py` — direct
  file reads, this session, establishing the existing patterns this phase must extend
- `requirements.txt` — direct read confirming no new packages are needed
- `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/STATE.md`,
  `.planning/phases/03-.../03-CONTEXT.md`, `SIGNOZ-RUNBOOK.md` — direct reads, this session

### Secondary (MEDIUM confidence)
- [SigNoz — Configure Webhook Channel](https://signoz.io/docs/alerts-management/notification-channel/webhook/) — webhook payload shape, `POST /api/v1/channels` config fields
- [SigNoz — Dashboards V2 API](https://signoz.io/docs/dashboards/dashboards-v2-api/) — `/api/v2/dashboards` CRUD/PATCH schema
- [SigNoz — Import Dashboard](https://signoz.io/docs/dashboards/import-dashboard/) — manual export/import UI steps
- [SigNoz — Alerts](https://signoz.io/docs/alerts/) — five alert-rule types (metrics/logs/traces/anomaly/exceptions)
- [SigNoz — Post-Deployment Monitoring with AI](https://signoz.io/docs/ai/use-cases/post-deployment-monitoring/) — confirms manual-timestamp workaround, no marker API
- [SigNoz — Agent Skills](https://signoz.io/docs/ai/agent-skills/) — confirms alert/dashboard skills exist but no deployment-marker/annotation mention

### Tertiary (LOW confidence)
- [github.com/SigNoz/signoz issue #6162](https://github.com/SigNoz/signoz/issues/6162) — "Ability to add annotations to panels in dashboards. Eg, deployment markers" — closed, but exact closure reason/date not retrievable via WebFetch this session; treat as directional evidence (A1 in Assumptions Log), not a definitive negative proof
- [github.com/SigNoz/signoz issue #11657 "Deploy guardian"](https://github.com/SigNoz/signoz/issues/11657) — a hackathon proposal referencing correlating CI/CD deployment markers with regressions; confirms the *concept* is not yet a shipped SigNoz feature, corroborating A1
- community-chat.signoz.io thread on deployment markers — could not be fetched this session (DNS resolution failure on `community-chat.signoz.io`); referenced only via WebSearch summary, not independently verified — treat with caution

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all versions read directly from `requirements.txt`
- Architecture (flag store, injectors, route ordering): HIGH — directly extends patterns already
  verified in the existing codebase
- Deployment marker mechanism (Key Finding 1 / A1): MEDIUM — corroborated by two independent
  sources (closed feature request + AI use-case doc workaround) but the primary community-chat
  thread could not be fetched; recommend a quick live-SigNoz UI check at HV-2 time to confirm no
  annotation feature has since shipped
- Webhook payload schema: MEDIUM — official SigNoz docs page fetched directly this session
- Alert rule / SLO/burn-rate mechanics: LOW-MEDIUM — official docs confirm alert *types* exist but
  provide no SLO-object/burn-rate-specific UI walkthrough; hand-building this will likely require
  live UI exploration during HV-2, not something fully specifiable from docs alone

**Research date:** 2026-07-24
**Valid until:** 2026-08-07 (14 days — SigNoz is an actively developed product; re-verify the
deployment-marker/annotation gap (A1) if this research is reused past that window, in case a
native feature ships)
