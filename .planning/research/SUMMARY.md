# Project Research Summary

**Project:** Agent K — The Evidence-First Incident Agent
**Domain:** Evidence-first, safety-gated, self-observing AI incident-response agent (FastAPI RAG service + Python state-machine agent, on SigNoz/OpenTelemetry/Foundry/OpenRouter)
**Researched:** 2026-07-20
**Confidence:** MEDIUM-HIGH

## Executive Summary

Agent K is buildable exactly as locked in PROJECT.md — the four research passes found no reason to change scope — but two things must change immediately or the project cannot produce its own evidence: **(1) buy $10 of OpenRouter credit on Day 1.** A fresh OpenRouter account is capped at 50 free-model requests/day; the locked eval plan (4 incidents x 3 runs, each run making 5-15+ LLM calls once RAG traffic, retries, and report generation are counted) can burn through that in a single day of dry-run testing, let alone the actual eval matrix. $10 lifetime credit permanently raises the cap to 1,000/day. This is not a nice-to-have; it's a blocker on the project's own success criteria, and it is invisible until a 429 shows up mid-investigation — possibly on demo day. **(2) Several PROJECT.md assumptions are stale and must be corrected before code is written**, most importantly: the GenAI semantic-convention attribute names have been renamed upstream (`gen_ai.provider.name`, `gen_ai.usage.input_tokens`/`output_tokens` — not the deprecated `gen_ai.system`/`prompt_tokens`/`completion_tokens`), SigNoz has no native deployment-marker API (build one as a custom OTel span instead), `casting.yaml.lock` is a checksum/drift-detection file rather than a dependency lockfile (image tags must be pinned by hand), the documented fallback model `cohere/north-mini-code:free` lacks `structured_outputs` support (a materially weaker fallback than assumed), and Foundry exposes the SigNoz MCP server as a first-class molding (`spec.mcp.spec.enabled: true`) rather than something stood up via a standalone `docker run`.

Beyond those corrections, the research converges on one architectural signal that deserves top billing in both the build and the demo narrative: **only the `hypothesize` pipeline stage may call an LLM.** `collect`, `validate`, `policy_gate`, `act`, and `verify` must be pure, unit-testable code with zero model dependency in the decision path. This is the literal, checkable definition of "Three Laws enforced by code, not prompt" — a judge (or a unit test) can verify it by grep-ing for LLM client imports outside `hypothesize.py` and `llm.py`. The single largest correctness risk sitting next to this is the safety gate: with only four fixed incidents and a 2-approve/2-deny target, the fastest path under time pressure is to tune thresholds until the four incidents produce the right split — which overfits the gate to exactly the scenarios the team designed and directly undermines the "code-enforced, not vibes" thesis the moment a judge varies a parameter. The mitigation (decision table + per-check unit tests on synthetic inputs, written before any incident is run end-to-end, with each incident deliberately designed to fail one *named* check) must happen on Day 4, before implementation, not as post-hoc debugging.

Feature and architecture research also converge on a positioning point worth stating plainly for both the build and the blog: SigNoz has already published prior art (a LangChain agent querying SigNoz MCP, with a dashboard tracking the agent's own latency/tokens/errors) that covers the *read path* — an agent that queries observability data and is itself partially observable. Agent K's novelty is not "an agent that talks to SigNoz MCP." It is the three enforcement layers wrapped around that read path: a validator that structurally deletes unsupported claims, a policy gate whose six checks are each their own auditable telemetry span, and self-observability that can *halt* an in-flight investigation (loop breaker, cost watchdog) rather than merely report on it. SigNoz's own "Agent-Native Observability" vision post names "investigation-to-policy workflows" as a *future*, unshipped roadmap item — Agent K is a working instance of exactly that. The build and the blog should both lead with the enforcement layer, not the MCP query capability, since the query capability alone would read as a near-duplicate of existing SigNoz material.

## Key Findings

### Recommended Stack

Python 3.11/3.12, FastAPI 0.139.x + Uvicorn (no `--reload` once OTel auto-instrumentation wraps it), PostgreSQL 16/17 with `pgvector` 0.8.5 as the single datastore (must swap Foundry's stock Postgres image for `pgvector/pgvector:pg16` — the default image has no pgvector compiled in), OpenTelemetry SDK 1.44.0 paired with instrumentation packages on the independent `0.65b0` line, SigNoz deployed and pinned via Foundry (`foundryctl`), the SigNoz MCP server enabled as a Foundry molding, and OpenRouter as the sole LLM/embeddings provider via the standard `openai` Python SDK. All four PROJECT.md model slugs were confirmed live in OpenRouter's catalog; three support `structured_outputs`, the fourth (the documented fallback) does not.

**Core technologies:**
- FastAPI + Uvicorn — RAG service, zero-code OTel instrumentation via ASGI middleware
- PostgreSQL 16 + pgvector 0.8.5 — single datastore constraint, requires a pgvector-enabled image
- OpenTelemetry Python SDK 1.44.0 / instrumentation 0.65b0 — traces, metrics, logs; pin both lines together, this pairing is the single most common OTel-Python breakage point
- SigNoz + Foundry (`foundryctl`) — observability backend and deployment CLI; pin every molding's image tag explicitly for the clean-machine rebuild target
- SigNoz MCP server (Foundry molding, `spec.mcp.spec.enabled: true`) — the agent's only path to evidence; HTTP/Streamable-HTTP transport on port 8000, per-request `SIGNOZ-API-KEY` header
- OpenRouter (`openai` SDK, `base_url` swap) — chat + embeddings, single provider; compute cost from token counts against a configured price table, never from `usage.cost` (always `0` on `:free` models)

### Expected Features

Agent K's locked scope already clears essentially the entire table-stakes list for the AI-SRE/incident-copilot category (multi-signal telemetry, cross-signal correlation, deployment-awareness, ranked hypotheses with visible reasoning, human-readable report, recommendation-only fallback, cost/token instrumentation, read-only-by-default posture). Because of that, judges familiar with the category won't see the base loop as novel — the differentiators are where the pitch has to land, and PROJECT.md's locked scope already covers all of them.

**Must have (table stakes, already locked):**
- Multi-signal telemetry (traces + metrics + logs) with cross-signal correlation
- Deployment/change-awareness as an RCA input
- Ranked hypotheses with confidence and visible reasoning, not a bare verdict
- Human-readable Markdown incident report
- Recommendation-only fallback whenever confidence/preconditions aren't met

**Should have (differentiators, already locked — do not undersell these in the demo):**
- Code-enforced evidence validator that deletes unsupported claims before render (Agent K's single sharpest claim — no surveyed commercial competitor documents doing this structurally)
- Automated link-checker verifying every evidence link against the *live* SigNoz instance
- Span links connecting investigation spans to the original incident trace (a less-trodden usage of a SigNoz primitive whose public examples are async/background-job correlation, not agent-audit provenance)
- Six-check policy gate with every verdict emitted as its own telemetry span
- An actual gated action (rollback) evaluated with an explicit 2-approve/2-deny design
- Full self-observability that can *halt* an investigation (loop breaker, cost watchdog) — goes beyond SigNoz's own published prior art, which shows only passive agent dashboards
- Incident 2's cost-only failure mode (flat error rate, cost SLO breach) — not commonly staged in surveyed material and is explicitly the sharpest argument in the project

**Defer / explicitly out of scope (already locked, restated for roadmap awareness):**
- Kubernetes/worker queues/extra microservices, chat interface, unsupervised remediation, expanding the action allowlist, generic LLM cost tracker as the product, dashboards/alerts-as-code via Terraform (omitted, not deferred), any claim of production-grade accuracy from a 4-scenario sample

Two SigNoz feature-scope ambiguities flagged for requirements/roadmap resolution (not scope additions): whether "SLO breach" in the policy gate uses SigNoz's native SLO/burn-rate objects or an internally computed metric check (different query surfaces, resolve before building the policy module's SLO check), and whether deployment-marker comparison is exercised via SigNoz's own time-shift/Query-Builder mechanism or purely via the custom OTel span recommended in STACK.md (recommend the custom span — see Corrections below).

### Architecture Approach

An explicit Python state machine (no agent framework) with two structural safety properties: a `deployer` sidecar is the *only* component holding the Docker socket, so Agent K's worst-case blast radius from a reasoning bug or prompt injection is one authenticated HTTP call to an endpoint that does exactly one hardcoded thing (rollback, target decided server-side, never LLM-supplied); and a single `InvestigationState` Pydantic model threads through seven pipeline stages (`collect -> hypothesize -> validate -> policy_gate -> act -> verify -> report`), each a pure(ish), independently unit-testable function.

**Major components:**
1. `app` (FastAPI RAG service) — the monitored "patient"; owns Postgres+pgvector, calls OpenRouter, emits GenAI-semconv telemetry; has no knowledge it may be investigated or rolled back
2. `agent-k` — the state machine; owns every LLM call site and every MCP call site (this ownership is what makes exact per-call cost/token/duration accounting and the loop-breaker possible); the **only** stage permitted to call an LLM is `hypothesize`
3. `deployer` sidecar — minimal, dependency-isolated from `agent-k`'s codebase; sole Docker-socket holder; one endpoint, hardcoded rollback target, shared-secret auth, in-flight concurrency lock
4. SigNoz stack (Foundry-managed) + SigNoz MCP server — ingestion/query backend and the agent's only evidence-access path; agent's MCP client wrapper must be hardcoded to a read-only tool allowlist even though the server technically exposes mutating tools too

### Critical Pitfalls

1. **OpenRouter's 50-requests/day free-tier cap silently caps the entire eval matrix** — buy $10 credit on Day 1 (raises cap to 1,000/day permanently); instrument a live per-day counter from Day 1; do not discover this on demo day.
2. **The safety gate gets hand-tuned to hit 2-allow/2-deny instead of being correct by construction** — write per-check unit tests on synthetic inputs and a decision table *before* running any incident end-to-end; design each of the 4 incidents to fail one specific named check; treat "gate got the wrong verdict on incident N" as a bug in that check's logic, never as a threshold to nudge.
3. **OpenTelemetry silently drops exactly the telemetry the audit-trail thesis depends on** — short-lived processes (investigation runs, the rollback executor's request handler) exit before `BatchSpanProcessor`'s 5-second flush; call `force_flush()` explicitly at the end of every investigation and every rollback request; add a Day 1 startup self-check (emit span, flush, confirm queryable via MCP).
4. **The reasoning model has documented tool-call/structured-output drift** — validate every LLM response against schema in code, retry once with a stricter re-prompt, then fail explicitly and escalate (never silently self-correct a fabrication); confirm the fallback model's structured-output behavior before Day 5, not live during the demo (see Correction below — the documented fallback lacks `structured_outputs` support).
5. **Computed cost reads as fabricated unless loudly disclosed** — label every cost figure in-place ("computed, not billed"); treat missing `usage` data as an error to surface, never as silent $0; explicitly set `stream_options.include_usage=True` on every call.

## Corrections to PROJECT.md Assumptions

These are factual corrections surfaced by research, not new scope. Phase planning should treat PROJECT.md's current wording on these points as superseded and avoid propagating the stale version into implementation.

| PROJECT.md assumption | Correction | Source |
|---|---|---|
| `gen_ai.system`, `gen_ai.usage.prompt_tokens`/`completion_tokens` (implied by "GenAI semantic-convention attributes") | Spec renamed: use `gen_ai.provider.name` and `gen_ai.usage.input_tokens`/`gen_ai.usage.output_tokens`. Old names are deprecated, not merely alternate. Everything in the namespace is still `stability: development` — usable, just not GA. | STACK.md, verified directly against `open-telemetry/semantic-conventions-genai` registry |
| Implied deployment-marker capability in SigNoz for "deployment-related cause" checks | No native SigNoz deployment-marker/annotation API exists (absence confirmed across docs, MCP tool list, and use-case posts). Build one as a custom OTel span (`deployment.marker`, with version/timestamp attributes) emitted by the rollback executor — this is also the better philosophical fit, since it's an auditable, evidence-linkable span like everything else Agent K produces. | STACK.md, ARCHITECTURE.md |
| "`casting.yaml.lock` committed" implies a dependency lockfile (npm/poetry-style version pinning) | It is a checksum/state-tracking file that detects drift between declared and deployed config, not a transitive-dependency resolver. Image tags (`signoz/signoz`, `telemetrystore`, `metastore`, etc.) must still be pinned manually in `casting.yaml` for reproducibility — the lock file alone does not guarantee a judge's rebuild matches yours. | STACK.md |
| `cohere/north-mini-code:free` documented as "the fallback if agent schema adherence proves flaky" | Confirmed live in OpenRouter's catalog, but does **not** list `structured_outputs`/`response_format` in `supported_parameters`, unlike the other three pinned models. Falling back to it means falling back to prompt-engineered JSON with no API-level enforcement — a materially weaker reliability guarantee than the primary model, not a like-for-like swap. Test this explicitly before Day 5; do not treat it as a safe break-glass default. | STACK.md, PITFALLS.md |
| SigNoz MCP server assumed to be a standalone service the agent connects to | Foundry exposes it as a first-class **molding** (`spec.mcp.spec.enabled: true`) that auto-wires `SIGNOZ_URL` to the co-located apiserver, runs HTTP mode on port 8000 with a `/livez` healthcheck, and needs zero manual container wiring — materially better than the generic `docker run signoz/signoz-mcp-server` instructions in the MCP server's own README, which assume a standalone SigNoz you already have a URL for. Auth is per-request via a `SIGNOZ-API-KEY` header, minted from the SigNoz UI — not baked into `casting.yaml`. | STACK.md |

## The Cleanest Test of Agent K's Core Thesis

Elevate this as the operational definition of "enforced by code, not prompt," suitable for both a unit test and a one-line demo explanation: **only the `hypothesize` pipeline stage may call an LLM.** `collect` (fixed MCP query set), `validate` (strips claims with empty `evidence[]`), `policy_gate` (six pure checks), `act` (one authenticated HTTP call to the deployer), and `verify` (re-query MCP, compare) must all be pure code with zero model dependency in their decision path. Concretely: `policy_gate.py` should be unit-testable with zero LLM-client mocks, because it never imports one. The corresponding anti-pattern to explicitly avoid: adding an LLM-based "sanity check" inside `validate` or `policy_gate` ("ask the model if this looks safe") — this silently reintroduces model dependency into a safety property and makes the gate's outcome non-deterministic, exactly what PROJECT.md's Key Decision already forbids.

## Build-Order Corrections to the Locked 7-Day Plan

The locked day *headlines* are directionally sound and should not change — SigNoz must exist before anything can be queried, the pipeline shape must exist before individual Laws layer onto it, eval/demo must come last. But four items are scheduled as if they belong entirely to their headline day when they actually have an earlier dependency that, if left untouched until the headline day, creates avoidable schedule risk on the most safety-critical or highest-blast-radius parts of the system.

| Locked headline day | What the headline implies | What must be first-touched earlier | Why (what breaks if it isn't) |
|---|---|---|---|
| Day 1 — SigNoz + app + OTel | Telemetry plumbing only | The shared cost/price-table module (`agent/cost.py` or `infra/pricing.yaml`) | Day 2's cost SLO/alert (feeding Incident 2) needs a price-table lookup to exist; if "cost computation" is treated as Day 6 Law-3 work, Day 2 has nothing to alert on. Build it once on Day 1, reuse unmodified on Day 6. |
| Day 1-2 | — | `deployer/` sidecar skeleton (container, socket mount, one hardcoded rollback endpoint, auth, concurrency lock) | It has zero dependency on the agent's reasoning pipeline — only on `app` + versioned images existing. Leaving the single most safety-critical, highest-blast-radius component as a first-touch on Day 5 (alongside the policy gate and the 2/2 demo test) stacks three hard problems into one day. Scaffold and smoke-test it Day 1-2; Day 5 then only writes and wires the policy logic against an already-proven sidecar. |
| Day 3 — Agent workflow + MCP + RCA schema | Just wire the pipeline | An explicit decision on whether `collect`/`hypothesize` can loop (bounded, e.g. max 2 extra rounds) plus the query-hash tracking scaffold in `collect.py` | Law 3's loop breaker ("hashes MCP queries, halts on excessive repetition") only makes sense if a loop can occur — but PROJECT.md's own rationale for "no agent framework" says the investigation uses "a fixed query set," implying no loop. This is a real design fork Day 3 must resolve explicitly; retrofitting it painlessly on Day 6 is unlikely. Record query hashes as data on Day 3 even if the halt/escalate *policy* is genuinely Day 6 work. |
| Day 3 | Just call OpenRouter | Full per-LLM-call instrumentation (GenAI attributes, cost via the Day-1 price table, duration, emitted as spans/metrics) at `agent/llm.py`'s creation | The state-machine architecture is explicitly justified by "owning every LLM call site... makes exact token/cost/duration accounting possible" — that accounting should be built the same day the call site is built, not bolted on three days later. This also gives Days 3-5 real visibility into free-tier spend instead of flying blind, which matters directly for Pitfall 1 (the 50/day cap). |

Net effect on the locked days: Day 5 becomes lighter (wiring only, since `deployer/` and instrumentation are already proven), and Days 1 and 3 absorb a small amount of extra first-touch work that pays for itself by removing risk from the two hardest days (5 and 6).

## Implications for Roadmap

Given the fully-locked scope, phases should be organized around dependency order and risk-front-loading rather than feature grouping. Suggested phase structure (mapping cleanly onto, but refining, the locked 7-day headline days):

### Phase 1: Foundation — SigNoz, App, Telemetry, Sidecar Skeleton
**Rationale:** Nothing else can be built or verified without a running SigNoz instance and OTel data flowing; the deployer sidecar and price-table module have no dependency on the agent pipeline, so front-loading them here removes schedule risk from later, higher-stakes days.
**Delivers:** Foundry-deployed SigNoz with pinned image tags, FastAPI RAG app instrumented with GenAI-semconv-correct OTel (traces/metrics/logs), Postgres+pgvector as single datastore, `deployer/` skeleton (socket mount, one hardcoded endpoint, auth, concurrency lock) smoke-tested against a manual rollback, shared cost/price-table module.
**Addresses:** Table-stakes multi-signal telemetry ingestion; groundwork for the sandbox/deployer differentiator.
**Avoids:** Pitfall 1 (buy OpenRouter credit here, Day 1), Pitfall 3 (OTel endpoint/protocol self-check, force-flush pattern established from the start), Pitfall 7 (pin every image tag immediately, not retroactively).

### Phase 2: SLOs, Alerts, Deployment Markers, Seeded Incidents
**Rationale:** Incident-specific telemetry (cost SLO, deployment markers, fault-injection flags) must exist before the agent has anything realistic to investigate; this phase is parallelizable with Phase 3's early work since it lives entirely in the monitored app.
**Delivers:** SigNoz alerts (configured separately from the dashboard) reading real metrics including computed cost; custom OTel deployment-marker spans; four flag-controlled incident injections scoped to specific spans/operations with jitter and background traffic (not suspiciously clean signals).
**Uses:** SigNoz alert evaluation windows sized to fit the demo's compressed incident timeline; the deployer skeleton from Phase 1 for the deployment-marker emission point.
**Implements:** The "deployment-related cause" input the policy gate will later consume.
**Avoids:** Pitfall 8 (incidents too clean / not actually breaching SLO), Pitfall 12 (alert window vs. incident duration mismatch).

### Phase 3: Agent Core — State Machine, MCP, RCA Schema, Full LLM Instrumentation
**Rationale:** The pipeline shape (collect -> hypothesize -> ...) must exist and be fully instrumented before individual Laws can be layered onto discrete stages; this is also where the collect/hypothesize loop-or-not decision must be made explicitly.
**Delivers:** `InvestigationState` schema, all seven stage functions as independently unit-testable pure(ish) functions, MCP client wrapper restricted to a read-only tool allowlist, `agent/llm.py` as the single OpenRouter call site with full GenAI-attribute + cost + duration instrumentation from first commit, query-hash tracking scaffold in `collect.py`, centralized deep-link builder.
**Delivers:** The operational core of "only `hypothesize` calls an LLM."
**Avoids:** Pitfall 2 (schema-validate every LLM response, fail explicitly rather than silently retry-and-hope), Pitfall 9 (centralized, unit-tested link builder), Pitfall 13/14 (explicit empty-result and truncation handling).

### Phase 4: Law 1 — Evidence Validator and Link Checker
**Rationale:** Confirmed hard dependency: the policy gate's "confidence" check consumes already-validated claims, so this must precede Phase 5.
**Delivers:** Evidence validator that strips claims with empty `evidence[]` before render, automated link checker against the live SigNoz instance, span links from investigation spans to the original incident trace.
**Addresses:** The evidence-first differentiator — the single sharpest claim in the project.
**Avoids:** Pitfall 9 (deep-link resolution edge cases), Pitfall 10 (async context/log-trace correlation breaking span-link provenance).

### Phase 5: Law 2 — Policy Gate and Rollback Wiring
**Rationale:** By this point `deployer/` is already built and proven (Phase 1) and evidence/confidence signals already exist (Phase 4), so this phase is policy logic and wiring only, not infrastructure-plus-logic-plus-demo-validation in one day.
**Delivers:** Six-check policy module as a decision table with per-check unit tests written against synthetic inputs *before* any incident is run through it; every verdict emitted as its own telemetry span; end-to-end wiring producing 2 demonstrable approvals and 2 demonstrable denials, each incident engineered to fail one specific named check.
**Avoids:** Pitfall 4 (gate overfitting to the four seeded incidents) — this is the single highest-risk correctness issue in the project and this phase's central discipline.

### Phase 6: Law 3 — Self-Observability, Loop Breaker, Cost Watchdog, Dashboard
**Rationale:** Halting behavior is layered on top of instrumentation that has already been flowing (and been debugged) since Phase 3; the dashboard necessarily comes near-last since it aggregates every other phase's output.
**Delivers:** Loop breaker and cost watchdog that actually halt an in-flight investigation (not just log), missing-usage-data error path (never silent $0), retry/loop-breaker/cost-accounting reconciliation (attempted vs. billed calls kept as separate metrics), four-section SigNoz dashboard, metric-attribute cardinality review.
**Avoids:** Pitfall 5 (cost-figure disclosure), Pitfall 6 (retries corrupting loop-breaker or cost accounting), Pitfall 11 (cardinality explosion from per-investigation IDs on metric attributes).

### Phase 7: Eval, Clean-Machine Rebuild, Demo, Submission
**Rationale:** Needs the full pipeline, both approvals and both denials, and a proven rebuild, all already working — this phase verifies, it does not derive.
**Delivers:** 4 incidents x 3 runs with recorded accuracy/cost/time, scripted manual baseline, second independently-timed clean-machine rebuild (the first should already have happened by Day 5 per the mitigation below), demo footage against the locked script, submission blog written from the actual build log including failed/confusing runs, AI-assistance disclosure.
**Avoids:** Pitfall 7 (rebuild timing must be verified twice, not assumed) — recommend the first clean-machine timing test happen no later than what was Day 5 in the original plan, i.e., during Phase 5/6, not deferred entirely to this phase.

### Phase Ordering Rationale

- Foundation-first ordering is forced by data dependency: no evidence exists to collect until SigNoz + OTel + the app exist.
- The deployer sidecar and cost module are pulled forward from their "headline" days (5 and 6 respectively) because they have no dependency on the agent's reasoning pipeline and are either safety-critical (sidecar) or a hard prerequisite for an earlier phase's alerting (cost module) — see Build-Order Corrections above.
- Law 1 before Law 2 is a confirmed hard dependency (policy gate consumes validated claims).
- Law 3's halting logic is deliberately placed after its own instrumentation has had time to be exercised and debugged, consistent with "instrument at the call site, gate the behavior later."
- Eval/demo last is forced by needing the complete, working pipeline.
- The clean-machine rebuild timing check is pulled forward (mid-week) rather than left to the final phase, since fixing a >15-minute rebuild discovered on the last day is a high-cost, high-pressure fix.

### Research Flags

Phases likely needing deeper research during planning (`--research-phase`):
- **Phase 1:** Foundry's exact mechanism for co-locating non-SigNoz services (app, agent-k, deployer, postgres) on the same Docker network as Foundry's generated compose output was not conclusively confirmed from documentation — resolve directly against `SigNoz/foundry`'s moldings docs/examples before finalizing the top-level compose layout. Also verify live: `session.list_tools()` against the running MCP deployment (per-tool parameter schemas weren't independently confirmed), real deep-link URLs copied from the running SigNoz UI for each link type (trace, log query, dashboard panel, metric view — only the Logs Explorer format is officially documented; others are extrapolated).
- **Phase 2:** SigNoz webhook payload's exact default grouping delay (`group_wait`/`group_interval`) and whether SigNoz's routing-policy UI exposes tuning for it — a live demo-reliability risk; build a manual `/demo/trigger` fallback on `agent-k` regardless so the live demo doesn't depend on webhook timing.
- **Phase 3:** Whether the pinned free-tier OpenRouter models reliably honor `strict` structured output/function calling for the RCA schema under real (not training-era) conditions — treat as a first Day-3 task, not an assumption; the documented fallback model's weaker capability profile (see Corrections) raises the stakes here.
- **Phase 5:** The SLO-breach signal's implementation path (native SigNoz SLO/burn-rate object vs. internally computed metric check) is explicitly ambiguous in the current spec and has different query surfaces — resolve before writing the policy module's SLO-breach check, ideally during Phase 2's alert work.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 4:** Evidence-schema/validator pattern is a standard Pydantic-plus-pure-function design with no unusual integration surface.
- **Phase 6:** OTel metric cardinality management and cost-accounting discipline are well-established patterns with clear official guidance.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Package versions and GenAI semconv attribute names verified directly against source repos and PyPI; SigNoz MCP per-tool parameter schemas and some deep-link formats (beyond Logs Explorer) are extrapolated, not independently confirmed against a live instance |
| Features | MEDIUM-HIGH | SigNoz-specific claims are HIGH confidence (official docs/blogs read in full); commercial AI-SRE competitor claims are MEDIUM (vendor marketing, cross-checked 2-3 sources each, not independently benchmarked) |
| Architecture | MEDIUM-HIGH | Component boundaries and the deployer-sidecar safety pattern are HIGH confidence (official Docker/OTel/SigNoz docs); exact SigNoz webhook payload shape and Foundry's non-SigNoz-service co-location mechanism are MEDIUM — docs were sparse/new and only partially retrievable |
| Pitfalls | MEDIUM-HIGH | OpenTelemetry/FastAPI/SigNoz/OpenRouter mechanics verified via official docs and multiple independent sources; SigNoz MCP tool-level and Foundry lock-file behavior partially inferred; free-model-specific behavior (tool-call/JSON drift) is inherently volatile and should be re-verified on Day 1 against current model behavior, not trusted from this research alone |

**Overall confidence:** MEDIUM-HIGH — strong enough to plan against directly; the flagged gaps are all narrow, Day-1/Day-3-verifiable items, not open architectural questions.

### Gaps to Address

- Foundry's non-SigNoz-service co-location mechanism (moldings vs. sibling compose file) — resolve on Day 1 against `SigNoz/foundry` docs/examples before finalizing `docker-compose.yml` layout.
- SigNoz MCP per-tool parameter schemas (field names, time formats, filter shapes) — introspect live via `session.list_tools()` against the running deployment on Day 1; do not hardcode from documentation.
- Deep-link formats beyond Logs Explorer (traces explorer, trace-by-ID, dashboard panels) — click through the running SigNoz UI once per link type on Day 1 and reverse-engineer the link builder from the real generated URLs, not from extrapolation.
- SigNoz webhook grouping-delay tuning — verify on Day 2; build the `/demo/trigger` manual fallback regardless.
- Free-tier model structured-output/tool-call reliability, especially the fallback model's weaker capability profile — verify on Day 3, before committing to it as a break-glass option.
- SLO-breach implementation path (native SigNoz SLO object vs. internal computation) — a requirements-definition decision, not a research gap per se; resolve before Phase 5's policy module is built.

## Sources

### Primary (HIGH confidence)
- `github.com/open-telemetry/semantic-conventions-genai` (`registry.yaml`, `gen-ai-spans.md`)
- `github.com/SigNoz/foundry` (`docs/concepts/*`, `docs/reference/*`, `docs/examples/docker/compose-mcp/`)
- `github.com/SigNoz/signoz-mcp-server` (README)
- `openrouter.ai/docs/api-reference/*`, live `/api/v1/models` catalog
- `signoz.io/docs/*` (logs-url-for-explorer-page, alerts, alert-evaluation-patterns, instrumentation guide)
- PyPI JSON API
- `signoz.io/blog/monitoring-langchain-agent-querying-signoz-mcp-server`, `signoz.io/blog/signoz-mcp-log-trace-investigation`, `signoz.io/blog/introducing-agent-native-observability`

### Secondary (MEDIUM confidence)
- Commercial AI-SRE competitor claims (Cleric, Traversal, Rootly, incident.io, Datadog Bits AI)
- SigNoz MCP tool-level parameter schemas and some deep-link route extrapolations
- Foundry's non-SigNoz-service co-location (moldings) mechanism
- gpt-oss-20b-class structured-output/tool-call drift reports (multiple independent community bug reports)

### Tertiary (LOW confidence)
- SigNoz webhook default grouping-delay values
- Free-tier model behavior generally

---
*Research completed: 2026-07-20*
*Ready for roadmap: yes*
