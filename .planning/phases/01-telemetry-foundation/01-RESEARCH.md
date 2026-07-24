# Phase 1: Telemetry Foundation - Research

**Researched:** 2026-07-21
**Domain:** SigNoz self-hosted observability backend deployment (Foundry) + OpenTelemetry Python instrumentation for a minimal FastAPI service
**Confidence:** MEDIUM (package versions and OTel SDK patterns HIGH/verified; Foundry CLI behavior and SigNoz UI specifics MEDIUM/official-docs-cited; a critical D-02 fallback-path assumption was found to be broken by upstream deprecation — see below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SigNoz Install Path**
- **D-01:** Attempt Foundry (`foundryctl gauge` → `forge` → `cast`) first — it is the only path that produces the judged `casting.yaml`/`casting.yaml.lock` deliverable.
- **D-02:** Time-box Foundry troubleshooting to 2-3 hours on Day 1. If it is still blocking the team past that point, fall back to SigNoz's plain `docker-compose.yaml` (from the `SigNoz/signoz` repo) to unblock instrumentation work immediately, then retrofit `casting.yaml`/`.lock` once the stack is stable. A working demo with a retrofitted Foundry config beats a broken demo with a "correct" install path (per CLAUDE.md's own documented fallback pattern).
- **D-03:** Before any install attempt, bump Docker Desktop memory allocation to 6-8GB — research flagged ClickHouse memory starvation as the top Day-1 pitfall, and this is a five-minute preventable fix.

**Skeleton Service Scope**
- **D-04:** The "minimal FastAPI skeleton" (TELE-03) is built as a **real, reusable scaffold** — `app/main.py` with FastAPI + OpenTelemetry instrumentation wired correctly (FastAPI/SQLAlchemy/logging auto-instrumentation, OTLP exporter setup) — not a disposable smoke-test script. Phase 2 extends this exact scaffold with the real `/ask` endpoint and pgvector retrieval logic, rather than re-doing the OTel wiring from scratch.
- **D-05:** "Before any app logic is written" (the phase goal) means no `/ask` route or RAG logic yet — it does not mean the FastAPI service itself gets thrown away after this phase.

**Telemetry Exporter Strategy**
- **D-06:** Run the console exporter and the OTLP exporter **simultaneously, always on** — no env-var toggle to switch between them. Silent OTLP delivery failures were research-flagged as the #1 Day-1 pitfall; always-on dual export means the team can immediately see from console output whether spans are being generated at all, independent of whether they're reaching SigNoz, without restarting or reconfiguring anything.
- **D-07:** Use `opentelemetry-exporter-otlp-proto-http` (HTTP/protobuf, port 4318) as the OTLP exporter, per the locked stack decision — not gRPC.

**Rebuild-Time Measurement**
- **D-08:** Automate the TELE-02 rebuild-time measurement with a small wrapper script that times `foundryctl cast` end-to-end and appends the duration + timestamp to a `TELEMETRY-REBUILD-LOG.md` file in the repo. This produces a reproducible, judge-verifiable artifact instead of a manually-noted stopwatch time.

### Claude's Discretion
- Exact directory structure inside `app/` (e.g., `app/main.py` vs. `app/telemetry.py` module split) — plan/execute can decide based on what keeps the OTel setup code cleanly separated from future RAG logic.
- Whether the rebuild-timing wrapper script is a shell script or a short Python script — whichever is simpler given the team's tooling choices made during planning.
- Exact SigNoz Docker Compose resource limits beyond the 6-8GB Docker Desktop floor — fine-tune during setup if ClickHouse still struggles.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TELE-01 | SigNoz runs self-hosted via Foundry, with `casting.yaml` and `casting.yaml.lock` committed to the repo | Foundry `gauge → forge → cast` workflow documented below with exact commands, minimal `casting.yaml` schema, and where `casting.yaml.lock` comes from |
| TELE-02 | A clean-machine Foundry rebuild (fresh clone → running SigNoz) completes in under 15 minutes, measured and recorded, not assumed | Rebuild-timing wrapper script pattern and log-file format documented below; ties to Pitfall 10 in project PITFALLS.md |
| TELE-03 | A minimal FastAPI skeleton emits traces, metrics, and logs confirmed visible in the SigNoz UI, with a console-exporter fallback for debugging | Full dual-exporter OTel SDK wiring pattern (traces/metrics/logs), FastAPI/logging auto-instrumentation, and concrete SigNoz UI verification steps documented below |

</phase_requirements>

## Summary

This phase is pure infrastructure standup with zero application logic, and the biggest risk is not technical difficulty but the team's total lack of prior Docker/OTel/SigNoz/Foundry experience combined with one **broken assumption already baked into the locked D-02 decision**: the plain `docker-compose.yaml` fallback path the team is counting on **no longer exists in the `SigNoz/signoz` repo** — it was removed upstream as of SigNoz v0.130.0, with the project's own migration docs stating "SigNoz no longer distributes these files." This doesn't invalidate D-02's intent (having *a* fallback if Foundry blocks the team), but it means the literal mechanism described needs to change before Day 1 — see Common Pitfall 1 below for the concrete alternative.

Everything else about this phase follows the previously-completed project-level research closely: `foundryctl gauge → forge → cast` is a three-stage pipeline (validate → generate → deploy) driven by a small YAML file, and the OTel Python SDK natively supports registering multiple exporters (console + OTLP) on the same `TracerProvider`/`MeterProvider`/`LoggerProvider` without any custom plumbing — this is a first-class, documented pattern, not a workaround. `FastAPIInstrumentor.instrument_app(app)` and `LoggingInstrumentor().instrument(set_logging_format=True)` are both one-line calls that produce request-tracing and trace-correlated logs respectively. Verifying "visible in the SigNoz UI" is concrete and checkable: Traces Explorer, Logs Explorer, and the default "Last 30 minutes" time window are the three things to check, in that order.

**Primary recommendation:** Attempt Foundry per D-01/D-02 as planned, but replace the literal "pull SigNoz's plain docker-compose.yaml" fallback with "run `foundryctl forge` (file generation only, documented as safe/idempotent) then `docker compose up -d` directly against the generated `pours/deployment/compose.yaml`, bypassing `cast`'s orchestration layer" — this preserves the intent of D-02 (unblock via a lower-level mechanism) using tooling that still exists. Build the OTel dual-exporter wiring as one shared `app/telemetry.py` module Phase 2 can import from, and verify TELE-03 via SigNoz's Traces Explorer + Logs Explorer + a metrics query, in an explicitly widened time range if the first test trace predates the UI's default "Last 30 minutes" window.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SigNoz backend (ClickHouse, OTel Collector, query-service, frontend) | Database/Storage + API/Backend (self-hosted observability platform) | — | This is infrastructure being stood up, not app logic; it owns storage (ClickHouse) and its own query API/UI |
| Foundry CLI (`foundryctl`) deployment orchestration | Build/Deploy tooling (not a runtime tier) | — | Runs at deploy-time on the developer/CI machine, generates and applies Docker Compose config; has no runtime request path of its own |
| FastAPI skeleton service (`app/main.py`) | API/Backend | — | This is the "monitored service" — Phase 2 will add real endpoints here; in Phase 1 it exists solely to prove telemetry emission |
| OTel SDK instrumentation (traces/metrics/logs + exporters) | API/Backend (in-process SDK inside the FastAPI service) | — | Lives inside the same Python process as the FastAPI app; it is not a separate service — it pushes data out to the SigNoz Collector via OTLP |
| Console exporter fallback | API/Backend (in-process, stdout) | — | Same process as the OTel SDK; writes to the service's own stdout, no network dependency, used purely for local debugging |
| Rebuild-timing wrapper script | Build/Deploy tooling | — | A CI/dev-machine script wrapping `foundryctl cast`, not part of the running application |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.139.2 | Web framework for the minimal skeleton service | Locked stack choice; verified current on PyPI this session `[VERIFIED: PyPI JSON API — pypi.org/pypi/fastapi/json, checked 2026-07-21]` |
| `uvicorn[standard]` | 0.51.0 | ASGI server | Standard FastAPI companion `[VERIFIED: PyPI JSON API, checked 2026-07-21]` |
| `opentelemetry-api` + `opentelemetry-sdk` | 1.44.0 | Core tracing/metrics/logs SDK | Single SDK version covers all three signals `[VERIFIED: PyPI JSON API, checked 2026-07-21]` |
| `opentelemetry-exporter-otlp-proto-http` | 1.44.0 | OTLP HTTP/protobuf exporter (port 4318) — locked per D-07, not gRPC | Fewer TLS/port-forwarding surprises for a Docker-inexperienced team `[VERIFIED: PyPI JSON API, checked 2026-07-21]` |
| `opentelemetry-instrumentation-fastapi` | 0.65b0 | One-line auto-instrumentation of every FastAPI request as a span | `[VERIFIED: PyPI JSON API, checked 2026-07-21]` |
| `opentelemetry-instrumentation-logging` | 0.65b0 | Correlates Python `logging` records with active trace/span IDs | `[VERIFIED: PyPI JSON API, checked 2026-07-21]` |
| `python-dotenv` | 1.2.2 | Loads `.env` for SigNoz URL / OTLP endpoint config locally | `[VERIFIED: PyPI JSON API, checked 2026-07-21 — note: CLAUDE.md lists "latest", this is the exact resolved current version]` |
| `foundryctl` (SigNoz Foundry CLI) | latest via install script | Declarative SigNoz deployment producing `casting.yaml.lock` | Only path that satisfies TELE-01's committed-lock-file requirement `[CITED: github.com/SigNoz/foundry/blob/main/docs/reference/cli.md]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opentelemetry-sdk` `ConsoleSpanExporter`/`ConsoleMetricExporter` | bundled in `opentelemetry-sdk` 1.44.0 | Always-on console fallback per D-06 | No separate install — these classes ship inside `opentelemetry-sdk`, only `ConsoleLogExporter` needs the same package `[CITED: opentelemetry.io/docs/languages/python/exporters/]` |

Note: `opentelemetry-instrumentation-sqlalchemy` (also 0.65b0, listed in project-level STACK.md) is **not needed in Phase 1** — there is no database/SQLAlchemy usage until Phase 2's pgvector retrieval work. Do not install it yet; it belongs in Phase 2's dependency set. Including it now would be unused surface area with nothing to instrument.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `opentelemetry-exporter-otlp-proto-http` (locked) | `opentelemetry-exporter-otlp-proto-grpc` | Explicitly rejected per CLAUDE.md's "What NOT to Use" — gRPC adds TLS/HTTP2/port complexity that's harder to debug blind for a Docker-inexperienced team |
| Foundry `cast` full pipeline | `forge` (generate only) + manual `docker compose up -d` | Use this specifically as the D-02 fallback mechanism (see Common Pitfalls) — decouples file generation from deploy orchestration, isolating which stage is actually failing |
| Bash wrapper script for rebuild timing | Python wrapper script (`time.monotonic()` around `subprocess.run`) | Either works; Python gives easier structured markdown-table appending if the team is more comfortable in Python than bash — left to Claude's discretion per CONTEXT.md |

**Installation:**
```bash
# FastAPI skeleton + OTel dual-exporter wiring
pip install "fastapi==0.139.2" "uvicorn[standard]==0.51.0" "python-dotenv==1.2.2"
pip install "opentelemetry-api==1.44.0" "opentelemetry-sdk==1.44.0" \
  "opentelemetry-exporter-otlp-proto-http==1.44.0" \
  "opentelemetry-instrumentation-fastapi==0.65b0" \
  "opentelemetry-instrumentation-logging==0.65b0"

# Foundry CLI (once, from repo root — generates casting.yaml.lock on forge/cast)
curl -fsSL https://signoz.io/foundry.sh | bash
```

**Version verification:** All core package versions above were re-verified live against the PyPI JSON API this session (2026-07-21) and match exactly what CLAUDE.md's locked stack already documents — no drift found.

## Package Legitimacy Audit

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|----------------------|-----------|--------------|---------|-------------|
| fastapi | PyPI | released 2026-07-16 (5 days old) | not exposed via PyPI API (checker: `unknown-downloads`) | github.com/fastapi/fastapi | SUS (heuristic) | Approved — see note |
| uvicorn | PyPI | released 2026-07-08 | unknown-downloads | github.com/Kludex/uvicorn | SUS (heuristic) | Approved — see note |
| opentelemetry-api | PyPI | released 2026-07-16 | unknown-downloads | github.com/open-telemetry/opentelemetry-python | SUS (heuristic) | Approved — see note |
| opentelemetry-sdk | PyPI | released 2026-07-16 | unknown-downloads | github.com/open-telemetry/opentelemetry-python | SUS (heuristic) | Approved — see note |
| opentelemetry-exporter-otlp-proto-http | PyPI | released 2026-07-16 | unknown-downloads | github.com/open-telemetry/opentelemetry-python | SUS (heuristic) | Approved — see note |
| opentelemetry-instrumentation-fastapi | PyPI | released 2026-07-16 | unknown-downloads | github.com/open-telemetry/opentelemetry-python-contrib | SUS (heuristic) | Approved — see note |
| opentelemetry-instrumentation-logging | PyPI | released 2026-07-16 | unknown-downloads | github.com/open-telemetry/opentelemetry-python-contrib | SUS (heuristic) | Approved — see note |
| python-dotenv | PyPI | released 2026-03-01 | unknown-downloads | github.com/theskumar/python-dotenv | SUS (heuristic) | Approved — see note |

**Note on all "SUS" verdicts above:** The automated `package-legitimacy check` seam flagged every package here as `SUS` solely on two signals: `too-new` (based on the *latest release's* publish date, not overall package age) and `unknown-downloads` (the checker has no PyPI download-count integration, so this fires for every PyPI package regardless of popularity). All eight packages resolve to official, trusted GitHub organizations (`fastapi/fastapi`, `open-telemetry/opentelemetry-python(-contrib)`, `theskumar/python-dotenv`) and are the same exact packages/versions already independently verified via live PyPI lookup in this project's own `CLAUDE.md` locked stack. This is a systematic false-positive pattern for actively-maintained PyPI packages (frequent releases + no wired-up download metric), not a slopsquatting signal. Per protocol, the disposition remains flagged for planner awareness — **the planner should add one lightweight `checkpoint:human-verify` confirmation before the first `pip install` of this dependency set** (a single "these are the correct, official packages" sanity check), not a full blocking gate per package.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** all 8 core packages above — flagged due to a checker heuristic limitation for the PyPI ecosystem (see note), not genuine risk signals. One combined `checkpoint:human-verify` before first install is sufficient.

## Architecture Patterns

### System Architecture Diagram

```
 Developer machine (fresh clone)
        │
        │ 1. curl -fsSL https://signoz.io/foundry.sh | bash   (install foundryctl)
        ▼
 ┌───────────────────┐
 │ foundryctl gauge   │  validates Docker/Compose prerequisites
 └─────────┬─────────┘
           ▼
 ┌───────────────────┐        writes
 │ foundryctl forge   │ ─────────────────► pours/deployment/compose.yaml
 └─────────┬─────────┘        writes       casting.yaml.lock (checksums)
           ▼
 ┌───────────────────┐
 │ foundryctl cast    │  runs `docker compose up -d` from pours/
 └─────────┬─────────┘
           ▼
 ┌─────────────────────────────────────────────────────────┐
 │  SigNoz stack (Docker Compose, self-hosted)              │
 │  ┌───────────┐  ┌──────────────────┐  ┌───────────────┐ │
 │  │ ClickHouse│◄─┤ OTel Collector    │◄─┤ SigNoz query- │ │
 │  │ (storage) │  │ (OTLP :4317/:4318)│  │ service + UI  │ │
 │  └───────────┘  └────────▲──────────┘  │ (:8080)       │ │
 │                          │             └───────────────┘ │
 └──────────────────────────┼────────────────────────────────┘
                            │ OTLP/HTTP :4318 (traces, metrics, logs)
                            │
 ┌──────────────────────────┴───────────────────────────────┐
 │  Minimal FastAPI skeleton (app/main.py)                    │
 │                                                             │
 │  FastAPI app ──► FastAPIInstrumentor.instrument_app(app)    │
 │       │           (auto-spans every request, called AFTER  │
 │       │            routes are registered)                  │
 │       │                                                     │
 │       ▼                                                     │
 │  TracerProvider ──┬─► BatchSpanProcessor(ConsoleSpanExporter)  (stdout, always on)
 │                   └─► BatchSpanProcessor(OTLPSpanExporter :4318) (to Collector, always on)
 │  MeterProvider   ──┬─► PeriodicExportingMetricReader(ConsoleMetricExporter)
 │                    └─► PeriodicExportingMetricReader(OTLPMetricExporter :4318)
 │  LoggerProvider  ──┬─► ConsoleLogExporter (via LoggingHandler)
 │                    └─► BatchLogRecordProcessor(OTLPLogExporter :4318)
 │  LoggingInstrumentor().instrument(set_logging_format=True)
 │       (injects trace_id/span_id into every stdlib log line)
 └─────────────────────────────────────────────────────────────┘
                            │
                            ▼
         Human verifies in SigNoz UI (:8080):
         Traces Explorer → Logs Explorer → a metrics query
         (widen "Last 30 minutes" default window if needed)
```

### Recommended Project Structure
```
Agent-K/
├── casting.yaml              # Foundry deployment config (committed)
├── casting.yaml.lock         # Foundry-generated lock file (committed, TELE-01)
├── TELEMETRY-REBUILD-LOG.md  # Append-only rebuild-time measurement log (TELE-02)
├── scripts/
│   └── time-foundry-cast.sh  # (or .py) wraps `foundryctl cast`, appends duration+timestamp
├── app/
│   ├── main.py                # FastAPI app object + route registration (D-04 scaffold)
│   └── telemetry.py           # OTel SDK setup: providers, dual exporters, instrumentors
└── .env.example                # OTLP endpoint, service name, etc.
```

### Pattern 1: Dual-exporter OTel setup (console + OTLP, always on)
**What:** Register both a console exporter and an OTLP HTTP exporter as separate processors/readers on the same provider — never a single exporter with a toggle.
**When to use:** For every signal (traces, metrics, logs) in this phase, per D-06.
**Example:**
```python
# Source: opentelemetry.io/docs/languages/python/exporters/ (CITED, verified 2026-07-21)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

resource = Resource.create({SERVICE_NAME: "agent-k-rag-service"})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
)
trace.set_tracer_provider(tracer_provider)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(ConsoleMetricExporter()),
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint="http://localhost:4318/v1/metrics")
        ),
    ],
)
metrics.set_meter_provider(meter_provider)
```
Logs follow the same shape: a `LoggerProvider(resource=resource)` with two processors — one wrapping `ConsoleLogExporter()`, one wrapping `OTLPLogExporter(endpoint="http://localhost:4318/v1/logs")` — attached via a `LoggingHandler` on the root Python logger `[CITED: opentelemetry-python-contrib logging instrumentation docs + opentelemetry.io exporters docs]`.

### Pattern 2: FastAPI + logging instrumentation (one-liners, order matters)
**What:** Auto-instrument the app and correlate logs with traces with two library calls, no manual span code needed for basic request tracing.
**When to use:** In `app/main.py`, after all routes are registered.
**Example:**
```python
# Source: opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html (CITED)
import fastapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

app = fastapi.FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Must come AFTER route registration — instrumenting before routes exist
# means those routes are never wrapped.
FastAPIInstrumentor.instrument_app(app)

LoggingInstrumentor().instrument(set_logging_format=True)
# Injects %(otelTraceID)s / %(otelSpanID)s / %(otelServiceName)s into every
# stdlib logging record made while a span is active.
```

### Pattern 3: Foundry gauge → forge → cast, decoupled for debuggability
**What:** Run the three Foundry stages so a failure in `cast` (deploy orchestration) doesn't block you from at least confirming `forge` (file generation) succeeded.
**When to use:** Both for the primary D-01 attempt and as the D-02 fallback mechanism (see Common Pitfalls).
**Example:**
```bash
# Source: github.com/SigNoz/foundry/blob/main/docs/reference/cli.md,
# github.com/SigNoz/foundry/blob/main/docs/getting-started.md (CITED, verified 2026-07-21)

# casting.yaml (minimal, Docker Compose mode)
cat > casting.yaml <<'EOF'
apiVersion: v1alpha1
metadata:
  name: signoz
spec:
  deployment:
    mode: docker
    flavor: compose
EOF

foundryctl gauge -f casting.yaml         # validate prerequisites (Docker, Compose v2)
foundryctl forge -f casting.yaml -p ./pours   # generate pours/ + casting.yaml.lock
foundryctl cast -f casting.yaml          # full pipeline: gauge + forge + deploy

# If cast hangs/fails but forge succeeded, deploy manually to isolate the failure:
docker compose -f pours/deployment/compose.yaml up -d
docker compose -f pours/deployment/compose.yaml logs -f signoz-signoz-0
```

### Anti-Patterns to Avoid
- **Single exporter with an env-var toggle:** Explicitly rejected by D-06 — always run both console and OTLP exporters so telemetry generation and telemetry delivery are debugged as two independent variables, never conflated.
- **Calling `FastAPIInstrumentor.instrument_app(app)` before routes are registered:** Routes added after instrumentation are not wrapped — silently produces incomplete tracing that looks like it "works" for whichever routes existed at instrumentation time.
- **Assuming the legacy `SigNoz/signoz` plain `docker-compose.yaml` still exists as a fallback:** It has been removed upstream (see Common Pitfalls #1) — do not write a fallback runbook step that references cloning that file from the current repo.
- **Using gRPC OTLP (port 4317) "because it's the other supported option":** Explicitly rejected per CLAUDE.md/D-07 — HTTP/protobuf (4318) only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request-level tracing for FastAPI | Manual middleware wrapping every route in a span | `opentelemetry-instrumentation-fastapi`'s `FastAPIInstrumentor.instrument_app(app)` | One-line, handles ASGI lifecycle edge cases (exceptions, streaming responses) that a hand-rolled middleware would need to reimplement |
| Trace/log correlation | Manually injecting trace_id/span_id into log records via custom `logging.Filter` | `opentelemetry-instrumentation-logging`'s `LoggingInstrumentor().instrument(set_logging_format=True)` | Handles the OTel context lookup and format-string injection correctly across sync/async log call sites |
| Reproducible SigNoz deployment | Hand-maintained docker-compose.yml + manual env var docs | Foundry's `casting.yaml` + generated `casting.yaml.lock` | Lock file gives byte-for-byte reproducibility across machines — exactly what TELE-01/TELE-02 are judged on |
| Rebuild-time measurement | A one-off manual stopwatch note in a doc | A wrapper script appending timestamped durations to `TELEMETRY-REBUILD-LOG.md` | Produces a judge-verifiable, re-runnable artifact instead of an unverifiable claim (this is the entire point of D-08) |

**Key insight:** Nothing in this phase should be hand-rolled — OTel's Python SDK and SigNoz's own Foundry tooling already solve every problem this phase touches (instrumentation, exporting, reproducible deployment). The only genuinely custom code this phase produces is the thin rebuild-timing wrapper script, which is intentionally small.

## Common Pitfalls

### Pitfall 1: D-02's literal fallback mechanism ("pull SigNoz's plain docker-compose.yaml") no longer exists upstream
**What goes wrong:** If Foundry blocks the team past the 2-3 hour time-box, the plan (per D-02) is to fall back to SigNoz's plain `docker-compose.yaml` from the `SigNoz/signoz` repo. That file has been **removed from the repository as of SigNoz v0.130.0** — the project's own migration guide states "SigNoz no longer distributes these files, so this copy is your only way to roll back" (referring to a *user's own backed-up copy*, not a file still in the repo). A team executing D-02 literally will `git clone`/browse the current repo looking for `deploy/docker/clickhouse-setup/docker-compose.yaml` and not find it, burning more of the exact time-box the fallback exists to save.
**Why it happens:** SigNoz deprecated `install.sh` and the bundled Docker Compose files in favor of Foundry across a recent release; documentation and older blog posts/tutorials referencing the old path are still indexed and easy to find, creating the false impression the file still ships.
**How to avoid:** Change the concrete D-02 fallback mechanism to one of: (a) **preferred** — run `foundryctl forge` (file generation only; documented as safe, does not touch running containers) to produce `pours/deployment/compose.yaml`, then run `docker compose -f pours/deployment/compose.yaml up -d` directly, bypassing `cast`'s orchestration — this still uses Foundry (so the eventual `casting.yaml`/`.lock` commit is trivial, since forge already produced it) but isolates whether the failure is in `cast`'s extra logic or in the underlying Compose file itself; or (b) pin to a specific pre-v0.130.0 git tag of `SigNoz/signoz` to obtain the legacy compose file as a last resort, understanding it's now explicitly unsupported by SigNoz. This doesn't change the *intent* of D-02, only the literal mechanism, and should be treated as an update to the plan, not a re-litigation of the decision.
**Warning signs:** `git log`/browsing `SigNoz/signoz` for `deploy/docker/clickhouse-setup/docker-compose.yaml` and finding it absent from `main`; migration docs referencing "your own backed-up copy" instead of a repo-provided file.

### Pitfall 2: SigNoz + ClickHouse resource starvation (top Day-1 pitfall, already flagged in project research)
**What goes wrong:** ClickHouse Keeper segfaults (exit code 139) or the SigNoz UI never loads data, and it's mistaken for an instrumentation bug rather than a resource problem.
**Why it happens:** SigNoz's official minimum is 4GB Docker memory `[CITED: signoz.io/docs/install/docker/]`; the project's own PITFALLS.md research (already informing D-03's 6-8GB floor) found this insufficient under any real load on Docker Desktop defaults.
**How to avoid:** Bump Docker Desktop memory to 6-8GB before any install attempt (already locked as D-03). On Windows, prefer native Docker Engine inside WSL2 over Docker Desktop's Hyper-V/WSL2-backed VM if segfaults persist even after the memory bump `[CITED: web search cross-referencing SigNoz GitHub issues]`.
**Warning signs:** `docker ps` showing the Keeper/ClickHouse container repeatedly restarting; `docker logs` showing an OOM-kill or exit code 139.

### Pitfall 3: `foundryctl cast` run before `forge` succeeds, or run from the wrong directory
**What goes wrong:** Running `cast` (or manually running `docker compose up`) before the `pours/` directory has been generated produces a "compose file does not exist" error that looks like an install failure rather than a sequencing mistake.
**Why it happens:** `cast` runs gauge+forge+deploy automatically, but if a team member tries to shortcut by running `docker compose up` directly against a `pours/` directory that was never generated (e.g., after a `git clone` where `pours/` is gitignored — it should not be committed, only `casting.yaml`/`.lock` are), the file genuinely isn't there yet.
**How to avoid:** Always run `foundryctl cast -f casting.yaml` (which handles the full pipeline) for the primary path; only use the decoupled `forge` then manual `docker compose up -d` sequence deliberately, as the Pitfall 1 fallback — and confirm `pours/deployment/compose.yaml` exists before that manual step.
**Warning signs:** "compose file does not exist" error text.

### Pitfall 4: `casting.yaml.lock` not committed alongside `casting.yaml`
**What goes wrong:** TELE-01 requires both files committed; committing only `casting.yaml` means a judge's rebuild is not actually reproducible (config resolution/checksums are missing), even though the human-authored intent file is present.
**Why it happens:** `casting.yaml.lock` is auto-generated by `forge`/`cast`, easy to gitignore by habit (many teams reflexively ignore anything that looks like a lock/generated file).
**How to avoid:** Explicitly `git add casting.yaml casting.yaml.lock` and verify both are tracked (not gitignored) as part of this phase's definition of done.
**Warning signs:** `git status` showing `casting.yaml.lock` as untracked or ignored.

### Pitfall 5: First-time SigNoz UI check fails because of the default "Last 30 minutes" time window, not because telemetry isn't arriving
**What goes wrong:** A team generates one test trace, checks the SigNoz UI a few minutes later after debugging something else, and sees nothing — panicking that OTLP delivery is broken when the real issue is simply that the UI's default view window doesn't cover when the trace was actually sent, or no new traffic has been generated since.
**Why it happens:** SigNoz's Traces/Logs Explorer defaults to a "Last 30 minutes" rolling window `[CITED: web search of SigNoz userguide traces/logs explorer pages]`; this is a UX quirk, not a delivery problem, but looks identical to Pitfall 2 in PITFALLS.md ("traces exist but never reach SigNoz") from the outside.
**How to avoid:** When verifying TELE-03, generate fresh traffic (`curl localhost:8000/healthz` or similar) immediately before checking the UI, and explicitly widen the time range if in doubt, before concluding OTLP delivery is broken. Always check the console-exporter stdout output first (per D-06/Pitfall 2 in PITFALLS.md) — if spans print to console but don't appear in SigNoz within a widened time window, that isolates a real delivery problem; if nothing prints to console, the app isn't generating spans at all.
**Warning signs:** No data in SigNoz UI on a first check with a narrow/default time range, but the console exporter output shows the span was created.

## Runtime State Inventory

> Not applicable — this is a greenfield phase in a greenfield repository (per CONTEXT.md: "None yet — this is a greenfield repository"). No rename/refactor/migration is occurring. Skipping per template guidance for greenfield phases.

## Code Examples

Verified patterns from official sources (all confirmed live 2026-07-21):

### Minimal `casting.yaml` (Docker Compose mode)
```yaml
# Source: github.com/SigNoz/foundry/blob/main/docs/getting-started.md (CITED)
apiVersion: v1alpha1
metadata:
  name: signoz
spec:
  deployment:
    mode: docker
    flavor: compose
```

### Rebuild-time wrapper script (bash variant, D-08)
```bash
#!/usr/bin/env bash
# Source: this agent's synthesis, not from an external doc — [ASSUMED] pattern,
# straightforward use of standard shell timing constructs.
set -euo pipefail
START=$(date +%s)
foundryctl cast -f casting.yaml
END=$(date +%s)
DURATION=$((END - START))
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf "| %s | %ds |\n" "$TIMESTAMP" "$DURATION" >> TELEMETRY-REBUILD-LOG.md
echo "Foundry cast completed in ${DURATION}s — logged to TELEMETRY-REBUILD-LOG.md"
```
`TELEMETRY-REBUILD-LOG.md` should be initialized with a markdown table header (`| Timestamp (UTC) | Duration |` / `|---|---|`) so each run appends a clean row.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `install.sh` + bundled `docker-compose.yaml` in `SigNoz/signoz` repo | `foundryctl` (`gauge`/`forge`/`cast`) driven by `casting.yaml` | Deprecated as of SigNoz v0.130.0 `[CITED: github.com/SigNoz/signoz/issues/10924, deploy/MIGRATION.md]` | The plain-compose fallback path assumed in D-02 must be replaced with a Foundry-based decoupling (forge-then-manual-compose), not a literal legacy-file pull |
| gRPC OTLP as a commonly-tutorialed default | HTTP/protobuf OTLP (port 4318) preferred for this team | N/A — locked project decision (D-07), not an industry-wide shift | Simpler debugging surface; no separate "state of the art" claim beyond the project's own locked rationale |

**Deprecated/outdated:**
- SigNoz's legacy `install.sh` and bundled Docker Compose files: fully removed from the `SigNoz/signoz` repo as of v0.130.0; any tutorial/blog post referencing `deploy/docker/clickhouse-setup/docker-compose.yaml` in the current repo is stale.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The rebuild-time wrapper script pattern (bash `date`-based timing, appending a markdown table row) is a reasonable, low-risk approach for D-08 | Code Examples | Low — this is a simple, easily-testable script; worst case it needs a minor rewrite, no external dependency risk |
| A2 | No additional Docker Desktop CPU-allocation guidance exists beyond the memory figure already covered by D-03 | Common Pitfalls / Environment Availability | Low — if ClickHouse still struggles after the 6-8GB memory bump, the team has explicit discretion (per CONTEXT.md) to tune further during setup |
| A3 | `foundryctl`'s exact typical first-time deployment duration (for gauging TELE-02's 15-minute budget) was not documented anywhere found this session | Summary / Open Questions | Medium — the team must empirically measure this themselves per D-08, which is exactly what the requirement already demands; this assumption only affects whether the team should expect close-call timing |

**If this table is empty:** N/A — see rows above; all are LOW-MEDIUM risk and don't block planning.

## Open Questions

1. **Exact first-time `foundryctl cast` duration on a genuinely clean machine**
   - What we know: Official docs don't state a typical duration; a related but different tool (ClickStack, a competing self-hosted observability stack) reports "under 15 minutes" for its own Docker quickstart, which is only weak circumstantial signal, not a SigNoz-specific number.
   - What's unclear: Whether SigNoz's own image pull + ClickHouse startup + first UI availability reliably lands under the 15-minute TELE-02 budget on a genuinely cold-cache machine.
   - Recommendation: This is precisely what TELE-02 requires the team to measure directly (per D-08) — treat the first real run as the actual answer, and if it's a close call, the largest likely time cost is Docker image pulls (mitigate by ensuring the wrapper script's timer starts only after `foundryctl gauge` confirms prerequisites, not including the one-time `foundryctl` binary install itself, which is arguably outside "fresh clone → running SigNoz").

2. **Whether `pours/` should be gitignored**
   - What we know: `pours/` is Foundry's generated-output directory (compose files, resolved config); `casting.yaml` and `casting.yaml.lock` are the two files TELE-01 explicitly requires to be committed.
   - What's unclear: Official Foundry docs don't explicitly state a recommended `.gitignore` policy for `pours/`.
   - Recommendation: Gitignore `pours/` (it's regenerable from `casting.yaml` via `forge`) and commit only `casting.yaml` + `casting.yaml.lock` — this matches the stated purpose of the lock file (deterministic regeneration) and avoids committing machine-specific absolute paths that may leak into generated compose files.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Desktop / Docker Engine + Compose v2 | Entire phase — SigNoz stack, FastAPI skeleton | Not verified this session (team-machine-dependent, zero prior experience per CONTEXT.md) | — | None — this is a hard blocking dependency; Day 1 must include an explicit `docker compose version` smoke test on every teammate's machine before any other work |
| `foundryctl` binary | TELE-01 (Foundry deployment) | Not yet installed (installed via `curl -fsSL https://signoz.io/foundry.sh \| bash` as part of this phase's first task) | latest at install time | If install script fails, check GitHub releases page for a manual binary download per platform |
| Python 3.11 or 3.12 | FastAPI skeleton, OTel SDK | Not verified this session | — | None with a fallback — locked per CLAUDE.md; avoid 3.13 this week per CLAUDE.md's own note about contrib package lag |

**Missing dependencies with no fallback:**
- Docker Desktop/Engine + Compose v2 must be confirmed working on every teammate's machine before Day 1 work proceeds — this blocks the entire phase if absent.

**Missing dependencies with fallback:**
- `foundryctl` install script failure has a documented manual-binary fallback via GitHub releases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None yet exists in this greenfield repo. `pytest` + `pytest-asyncio` are the project's locked choice (CLAUDE.md) but no config file exists yet. |
| Config file | none — see Wave 0 |
| Quick run command | `pytest -q` (once bootstrapped) |
| Full suite command | `pytest` (once bootstrapped) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TELE-01 | `casting.yaml`/`casting.yaml.lock` exist, are committed, and `foundryctl cast` succeeds | smoke (manual/scripted, not pytest — this is an infra standup check, not application logic) | `git ls-files casting.yaml casting.yaml.lock` (both must return non-empty) + `foundryctl cast -f casting.yaml && docker ps` | ❌ Wave 0 (no automation exists yet; this phase creates the check itself) |
| TELE-02 | Rebuild completes under 15 minutes, measured | smoke (scripted, via wrapper script itself — this requirement's "test" IS the deliverable) | `scripts/time-foundry-cast.sh` (or `.py`) then inspect `TELEMETRY-REBUILD-LOG.md` for a duration < 900s | ❌ Wave 0 — this phase builds the script |
| TELE-03 | Traces/metrics/logs from the FastAPI skeleton are visible in SigNoz UI | manual-only (UI verification is not automatable within this phase's scope — no SigNoz query API client exists yet; that's Phase 4/MCP's job) | `curl localhost:8000/healthz` to generate traffic, then manual check of Traces Explorer / Logs Explorer / a metrics panel in SigNoz UI at `localhost:8080` | ❌ Wave 0 (manual-only check, documented as such is acceptable — this requirement is inherently a human-verified UI check per its own wording "confirmed visible in the SigNoz UI") |

### Sampling Rate
- **Per task commit:** Manual smoke checks per the table above (this phase has no automated unit-test surface — it is infrastructure standup and a thin skeleton service with no business logic to unit test yet)
- **Per wave merge:** Full manual verification pass: rebuild timing + SigNoz UI check together
- **Phase gate:** All three requirements' checks pass together before `/gsd-verify-work` — TELE-01 (files committed + cast succeeds), TELE-02 (logged duration < 15 min), TELE-03 (UI shows traces/metrics/logs)

### Wave 0 Gaps
- [ ] `scripts/time-foundry-cast.sh` (or `.py`) — covers TELE-02, does not yet exist
- [ ] No `pytest` infrastructure needed yet for this phase specifically (no business logic exists) — first real test files arrive in Phase 2 when `/ask` endpoint logic exists to test
- [ ] `TELEMETRY-REBUILD-LOG.md` — needs to be initialized with a markdown table header before first script run

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | This phase has no user-facing auth surface — FastAPI skeleton has no endpoints beyond a health check |
| V3 Session Management | No | No sessions in this phase |
| V4 Access Control | No | No access-controlled resources yet |
| V5 Input Validation | No (deferred to Phase 2) | The skeleton has no request bodies/params to validate yet — `/ask` and its `pydantic` schema arrive in Phase 2 |
| V6 Cryptography | No | Nothing in this phase requires cryptographic operations |
| V13 Configuration (adjacent concern) | Yes | SigNoz's default install has no auth in front of the UI (`localhost:8080`) out of the box in a local dev/demo context; do not expose this port beyond localhost/the team's own network during the hackathon — note as an operational caution, not a code-level control, since this is a self-hosted, non-internet-facing hackathon deployment |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Exposing SigNoz UI (port 8080) or OTLP ingest port (4318) to a public network interface unintentionally | Information Disclosure / Tampering | Keep Docker Compose port bindings scoped to `127.0.0.1` (or the team's private network) unless a later phase explicitly requires external exposure (e.g., the alert webhook in Phase 3/5) — this phase should default to localhost-only bindings |
| Committing secrets in `.env` accidentally | Information Disclosure | Ensure `.env` is gitignored from the very first commit of this phase; only `.env.example` (with placeholder values) is committed — this is a Day-1 hygiene item worth calling out explicitly since it's the team's first commit with any config file |

## Sources

### Primary (HIGH confidence)
- PyPI JSON API direct lookups (`pypi.org/pypi/<package>/json`) for fastapi, uvicorn, opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-logging, python-dotenv — all confirmed live 2026-07-21, matching CLAUDE.md's locked versions exactly

### Secondary (MEDIUM confidence — official docs, cited via WebFetch/WebSearch)
- [SigNoz Foundry CLI reference](https://github.com/SigNoz/foundry/blob/main/docs/reference/cli.md) — gauge/forge/cast commands, flags, casting.yaml.lock behavior
- [SigNoz Foundry getting-started guide](https://github.com/SigNoz/foundry/blob/main/docs/getting-started.md) — install script, minimal casting.yaml, deployment sequence
- [SigNoz Docker Standalone install docs](https://signoz.io/docs/install%2Fdocker/) — memory requirements, ports, confirms legacy path deprecated as of v0.130.0
- [SigNoz/signoz MIGRATION.md](https://github.com/SigNoz/signoz/blob/main/deploy/MIGRATION.md) — confirms legacy docker-compose.yaml removed from repo, rollback requires user's own backup
- [SigNoz/signoz install.sh deprecation issue #10924](https://github.com/SigNoz/signoz/issues/10924) — deprecation rationale, no upgrade/rollback path in old tooling
- [OpenTelemetry Python exporters docs](https://opentelemetry.io/docs/languages/python/exporters/) — multi-exporter TracerProvider/MeterProvider pattern, code verified
- [OpenTelemetry FastAPI instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html) — instrument_app() usage, ordering requirement, excluded_urls
- [OpenTelemetry logging instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html) — set_logging_format, trace/span correlation placeholders
- [SigNoz Foundry issue #89 — ARM64 macOS chown bug](https://github.com/SigNoz/foundry/issues/89) — known cast failure mode
- [SigNoz Docker troubleshooting FAQ](https://signoz.io/docs/setup/docker/troubleshooting/faq/) — general troubleshooting reference

### Tertiary (LOW confidence — web search only, not independently cross-verified)
- SigNoz UI default "Last 30 minutes" time-range behavior and Traces/Logs Explorer verification flow (WebSearch synthesis of SigNoz userguide pages)
- Docker Desktop memory allocation guidance for ClickHouse beyond the official 4GB minimum (WebSearch synthesis, no single authoritative source found beyond the project's own already-existing PITFALLS.md research)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version independently re-verified live against PyPI this session, matching the project's own locked CLAUDE.md exactly
- Architecture (OTel dual-exporter pattern, FastAPI instrumentation): HIGH — patterns confirmed via official OpenTelemetry and opentelemetry-python-contrib documentation, code examples are direct quotes/adaptations from those docs
- Foundry workflow: MEDIUM — official docs confirm command syntax and casting.yaml schema, but exact first-time deployment duration and some failure-mode details rely on GitHub issues and community reports rather than a single canonical troubleshooting doc
- Pitfalls: MEDIUM-HIGH — the critical D-02 fallback-path finding (legacy docker-compose.yaml removed upstream) is independently confirmed by two separate official sources (SigNoz docs + MIGRATION.md + the deprecation issue itself); other pitfalls corroborate the project's own existing PITFALLS.md research

**Research date:** 2026-07-21
**Valid until:** 7 days (fast-moving — SigNoz/Foundry is an actively evolving tool per this session's own discovery of a recent breaking deprecation; re-verify the Foundry CLI behavior and legacy-path status if this research is reused after the hackathon's 7-day window closes)
