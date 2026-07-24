# Phase 03 Context: Failure Injection + Dashboard + Alerting

**Created:** 2026-07-24
**Phase goal (from ROADMAP.md):** Each of the four seeded failure scenarios can be toggled live and observed happening in SigNoz, and a threshold breach reliably fires a webhook Agent K can receive.
**Depends on:** Phase 2 (RAG `/ask` pipeline)
**Requirements covered:** FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05, FLAG-06, DASH-01, DASH-02, DASH-05

## Domain

This phase makes the monitored RAG service *fail on demand* in four documented ways, surfaces
those failures in a hand-built SigNoz dashboard, and wires SigNoz alert rules to fire a webhook
Agent K can later consume. It is the bridge between "an observable app" (Phase 2) and "an agent
that investigates real incidents" (Phase 5). Two of the four deliverables are code
(fault injection + webhook receiver); two are hand-built in the SigNoz UI (dashboard + alerts).

The four seeded scenarios and their injection points in the existing codebase:

| Scenario | Requirement | Injection point (existing file) | Documented symptom |
|----------|-------------|----------------------------------|--------------------|
| Prompt regression | FLAG-02 | `SYSTEM_PROMPT` in [app/rag.py](../../../app/rag.py) — swap to a broken variant | Rising failed-answer rate; **has** deployment marker |
| Retry storm | FLAG-03 | timeout/retry loop around [app/llm.py](../../../app/llm.py) `generate()` | Cost/call-rate spike past cost SLO, HTTP error rate not necessarily up; **has** deployment marker |
| Retrieval latency | FLAG-04 | `retrieve()` in [app/rag.py](../../../app/rag.py) — artificial delay before/around the pgvector query | Slow `rag.retrieval` spans in the waterfall; **no** deployment marker |
| DB-pool exhaustion | FLAG-05 | engine/pool config in [app/db.py](../../../app/db.py) — reduce connections | Connection-pool-exhaustion errors in logs correlated to failed traces; **no** deployment marker |

## Decisions

### Feature-flag service (FLAG-01)
- **Single admin endpoint + token.** `POST /admin/flags` accepts JSON `{name, enabled}`;
  `GET /admin/flags` returns the current state of all four flags. State lives in an in-memory
  module-level store (dict), read **fresh per request** at each injection point — no restart to
  toggle (FLAG-01), no persistence across restart (matches spec's in-memory intent).
- **Auth:** guarded by a shared-secret `X-Admin-Token` header sourced from env. If the env var is
  **empty/unset, the endpoint is open** — deliberate so the local demo/eval harness works without
  ceremony. When set, a mismatch returns 401.
- **Registration order:** admin routes MUST be registered before `FASTAPIInstrumentor.instrument_app(app)`
  in [app/main.py](../../../app/main.py), same as `/ask` — anything registered after that call is
  never wrapped in spans (see the anti-pattern note at the top of main.py).

### Deployment markers (FLAG-06)
- **SigNoz API call on toggle.** When a *deployment-class* scenario (prompt-regression, retry-storm)
  is toggled **on**, the app makes an explicit call to SigNoz to create a deployment / change-event
  marker so it appears live in the dashboard's Incident Context. The two *non-deployment* scenarios
  (retrieval-latency, DB-pool-exhaustion) deliberately skip this call — that asymmetry is the whole
  point of FLAG-06 and Success Criterion 2.
- **Rejected:** encoding the version in the OTel resource and bumping it per scenario. The OTel
  resource is fixed at process start, so a live flag toggle can't change it without a restart —
  directly conflicts with FLAG-01's no-restart requirement.
- **For the researcher:** confirm the exact SigNoz mechanism/endpoint/payload for creating a
  deployment or change-event marker in the self-hosted (Foundry) build — API route, auth
  (SIGNOZ_API_KEY), and the field that distinguishes a deployment marker from a plain annotation.
  This is the highest-uncertainty item in the phase.

### Alert webhook receiver (DASH-05)
- **Reusable Agent K stub, not a throwaway.** Build a real `POST /alerts/webhook` entrypoint in its
  own module that validates, logs, and persists the incoming SigNoz alert payload. It is designed to
  be the actual trigger Agent K's Phase 5 investigation loop consumes — proving the entry path
  end-to-end now de-risks the reduced-capacity Phase 5 window.
- Must be reachable by the SigNoz alertmanager over the compose network. Payload shape and persistence
  format (what fields Agent K needs: alert name, severity, start time, affected service, related
  trace/label context) are for the researcher/planner to pin against SigNoz's actual webhook payload.

### Manual-UI vs code split (DASH-01/02/05)
- **Code now; SigNoz UI work captured as a runbook.** All codeable work — flag service, the four
  fault injectors, the deployment-marker emitter, the webhook receiver, and their tests — is built
  and verified in this phase without requiring a live SigNoz stack.
- The hand-built deliverables (Service Health + Incident Context dashboard sections, SLO/burn-rate/
  cost alert rules) are captured as **documented human-action steps** appended to
  [SIGNOZ-RUNBOOK.md](../../../SIGNOZ-RUNBOOK.md) (or a phase-local runbook), and the **exported
  dashboard/alert JSON is committed into the repo** (DASH-01 requires this) once the stack is live.
- The phase is **not blocked** on HV-2 (live SigNoz). Human-action items and the JSON-export step
  are tracked as pending verification, mirroring how Phase 2 handled HV-1/HV-2.

## Canonical Refs

Downstream agents (researcher, planner) MUST read these:
- [.planning/ROADMAP.md](../../ROADMAP.md) — Phase 3 section, Success Criteria (4 items)
- [.planning/REQUIREMENTS.md](../../REQUIREMENTS.md) — FLAG-01..06, DASH-01/02/05 exact wording
- [.planning/PROJECT.md](../../PROJECT.md) — locked scope, budget/provider constraints, Key Decisions
- [SIGNOZ-RUNBOOK.md](../../../SIGNOZ-RUNBOOK.md) — how the Foundry SigNoz stack is brought up (sec 1.5 first-run setup), where dashboard/alert JSON exports land
- [app/main.py](../../../app/main.py), [app/rag.py](../../../app/rag.py), [app/llm.py](../../../app/llm.py), [app/db.py](../../../app/db.py) — the four injection points + route-registration-before-instrumentation rule
- [app/observability.py](../../../app/observability.py) — single source of truth for `gen_ai.*`/`agentk.*`/`rag.*` attribute names; any new fault-injection metric/attribute must be defined here, not inline (avoids the D-06 attribute-drift that breaks dashboard queries)

_No external ADRs/specs beyond .planning docs were referenced during discussion._

## Code Context (reusable assets & patterns)

- **Fresh-per-call tracer pattern** — both `app/rag.py` and `app/llm.py` call `trace.get_tracer(__name__)`
  inside each function, never cached at import, so tests' monkeypatched provider is observed. New
  fault-injection spans/attributes must follow the same pattern.
- **`app/observability.py`** already centralizes attribute-name constants — extend it for any new
  fault or cost/marker attribute rather than hard-coding strings.
- **Route-before-instrumentation ordering** in `app/main.py` is a hard rule (documented anti-pattern).
- **Telemetry-proof pattern** — `scripts/probe_ask_spans.py` registers an observable TracerProvider in
  a fresh subprocess *before* importing `app.main` to measure the true production span set. Reuse this
  approach to prove a fault injector actually changes the emitted telemetry, rather than grepping for
  the call site (this is the lesson from 02-VERIFICATION.md gap 3).
- **Test suite** — `tests/` uses an `in_memory_exporter` fixture (conftest.py) + live-DB integration
  tests with `engine.dispose()` between event-loop boundaries. New injection tests follow those patterns.

## Deferred Ideas

- **DASH-03 (Agent Health) and DASH-04 (Action Audit Trail)** dashboard sections — intentionally
  deferred to Phase 7 per the roadmap (their data doesn't exist until Agent K / Law 2 are built).
  Not in this phase.

## Open Verification (carried, mirrors Phase 2 pattern)

- **HV-2 (from Phase 2, still open):** bring up the live SigNoz stack and confirm traces render.
  Phase 3's dashboard/alert JSON export and the end-to-end webhook-fire confirmation (Success
  Criterion 4) depend on this being done at least once.
- Building/exporting the dashboard + alert rules in the SigNoz UI is a human action captured in the
  runbook, verified when the stack is live.
