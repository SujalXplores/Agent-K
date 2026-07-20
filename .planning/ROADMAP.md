# Roadmap: Agent K — The Evidence-First Incident Agent

## Overview

Agent K is a seven-day hackathon build (2026-07-20 to 2026-07-26) delivered as horizontal layers, not vertical feature slices. The work starts with a running SigNoz instance, an instrumented FastAPI RAG app, and a proven rollback sidecar (Phase 1); adds realistic fault-injection and alerting so there is something worth investigating (Phase 2); builds the agent's state-machine pipeline with full LLM instrumentation (Phase 3); then layers the Three Laws on top one at a time — evidence validation (Phase 4), the policy gate and rollback wiring (Phase 5), and self-observability with halting behavior (Phase 6) — before a final phase proves the whole system against locked evaluation targets and packages it for submission (Phase 7). Most phases are not independently end-user-demoable until Phase 5 or later; that is expected, because the project's core value (evidence-backed claims, policy-gated actions) only becomes observable once all three enforcement layers exist together.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation — SigNoz, App, Telemetry, Sidecar Skeleton** - Running SigNoz via Foundry, instrumented FastAPI RAG app, and a smoke-tested deployer sidecar exist
- [ ] **Phase 2: SLOs, Alerts, Deployment Markers, Seeded Incidents** - The four fault-injectable incidents exist with real SLO breaches, alerts, and deployment markers to investigate
- [ ] **Phase 3: Agent Core — State Machine, MCP, RCA Schema, Full LLM Instrumentation** - Agent K's seven-stage pipeline runs end-to-end against SigNoz MCP with every LLM call fully instrumented
- [ ] **Phase 4: Law 1 — Evidence Validator and Link Checker** - No claim survives rendering without evidence, and every evidence link resolves live
- [ ] **Phase 5: Law 2 — Policy Gate and Rollback Wiring** - The six-check policy gate produces exactly 2 approvals and 2 denials across the seeded incidents
- [ ] **Phase 6: Law 3 — Self-Observability, Loop Breaker, Cost Watchdog, Dashboard** - Agent K can halt its own investigation and every signal is visible on one dashboard
- [ ] **Phase 7: Eval, Clean-Machine Rebuild, Demo, Submission** - Locked evaluation targets are met and the project is packaged for judges

## Phase Details

### Phase 1: Foundation — SigNoz, App, Telemetry, Sidecar Skeleton
**Goal**: A running SigNoz instance ingests correct telemetry from an instrumented FastAPI RAG app, and the deployer sidecar (the project's highest-blast-radius component) is scaffolded and proven this early rather than left to Day 5.
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06
**Success Criteria** (what must be TRUE):
  1. SigNoz is deployed via Foundry (`casting.yaml` + `casting.yaml.lock` committed, every image tag pinned) and reachable at its UI URL
  2. An OTel span emitted by the FastAPI app is visible in SigNoz within 30s of emission, confirmed via MCP query (not just the UI)
  3. A model call from the RAG app produces a span carrying `gen_ai.provider.name` and `gen_ai.usage.input_tokens`/`output_tokens` (current semconv names, not the deprecated ones)
  4. The `deployer/` sidecar's single `POST /rollback` endpoint, called manually with valid auth, actually rolls the app back to the previous version and returns success
  5. A clean-machine Foundry rebuild is timed at least once and completes in under 15 minutes
**Plans**: TBD

Plans:
- [ ] 01-01: TBD

### Phase 2: SLOs, Alerts, Deployment Markers, Seeded Incidents
**Goal**: The four seeded incidents exist as flag-controlled fault injections that produce genuine, non-trivial SLO breaches, deployment markers, and alerts — not suspiciously clean signals — giving Agent K something real to investigate.
**Depends on**: Phase 1
**Requirements**: INCD-01, INCD-02, INCD-03, INCD-04, INCD-05, INCD-06
**Success Criteria** (what must be TRUE):
  1. Triggering the prompt-regression flag raises the failed-answer rate and produces a `deployment.marker` OTel span correlated to the regression window
  2. Triggering the retry-storm flag breaches a cost SLO (computed via the Phase-1 price table) while the user-facing error rate stays flat or near-flat
  3. Triggering the retrieval-latency flag makes a pgvector retrieval span the dominant span in the trace waterfall, with no deployment marker in that window
  4. Triggering the database-pool-exhaustion flag produces connection-pool error logs correlated to failed traces via trace ID
  5. A SigNoz alert (separate from the dashboard) fires for each incident within the demo's compressed timeline, and `/demo/trigger` reliably surfaces the same incident without depending on webhook/alert timing
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: Agent Core — State Machine, MCP, RCA Schema, Full LLM Instrumentation
**Goal**: Agent K exists as an explicit seven-stage Python state machine that investigates a triggered incident end-to-end via SigNoz MCP, with only the `hypothesize` stage touching an LLM, and every LLM call fully instrumented from first commit rather than bolted on later.
**Depends on**: Phase 1, Phase 2
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05
**Success Criteria** (what must be TRUE):
  1. `collect`, `validate`, `policy_gate`, `act`, and `verify` contain zero LLM client imports, confirmed by grep/static check — only `hypothesize` imports the LLM client
  2. Agent K, given a manual trigger or alert webhook, derives its investigation time window from the alert's start time plus lookback buffer and runs its fixed MCP query set successfully against the read-only tool allowlist
  3. Every `hypothesize`-stage LLM call is recorded as Agent K's own telemetry span with GenAI attributes, computed cost (via the Phase-1 price table), and duration, visible in SigNoz
  4. The collect/hypothesize loop-or-not decision is explicit and implemented: bounded extra rounds if any, with MCP query hashes tracked as data in `collect.py` regardless
  5. A structured RCA claim (claim, confidence, evidence[]) is produced at the end of a full pipeline run for at least one seeded incident
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Law 1 — Evidence Validator and Link Checker
**Goal**: No RCA claim Agent K publishes can lack evidence — this is enforced by a renderer, not a prompt instruction — and every evidence link is proven to resolve against the live SigNoz instance.
**Depends on**: Phase 3
**Requirements**: LAW1-01, LAW1-02, LAW1-03, LAW1-04, LAW1-05
**Success Criteria** (what must be TRUE):
  1. A claim manually constructed with an empty `evidence[]` is stripped by the renderer before publish, verified by a unit test with zero LLM involvement
  2. Every evidence item in a rendered report carries a SigNoz deep link generated by the centralized link builder, and clicking/fetching that link resolves to real data in the running SigNoz instance
  3. An automated link checker run against a full incident report confirms 100% of rendered links resolve
  4. Agent K's investigation spans carry span links back to the original incident's traces, visible when inspecting either span in SigNoz
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Law 2 — Policy Gate and Rollback Wiring
**Goal**: A pure, unit-tested six-check policy module — built and tested against synthetic inputs before any incident runs through it — gates the single allowlisted action (rollback), and the four seeded incidents produce exactly the locked 2-approve/2-deny split by construction, not by tuning.
**Depends on**: Phase 1 (deployer sidecar), Phase 4 (validated claims/confidence)
**Requirements**: LAW2-01, LAW2-02, LAW2-03, LAW2-04, LAW2-05, LAW2-06, LAW2-07, LAW2-08
**Success Criteria** (what must be TRUE):
  1. `policy_gate.py` has a per-check unit test suite against synthetic inputs, written and passing before any seeded incident is run through the gate end-to-end
  2. The action allowlist contains exactly one entry (rollback), enforced in code
  3. Running all four seeded incidents through the full pipeline produces exactly 2 rollback approvals (Incidents 1, 2) and 2 rollback denials (Incidents 3, 4), each denial/approval traceable to one specific named failing/passing check, not a threshold adjustment
  4. Every policy verdict is emitted as its own telemetry span containing action, incident ID, SLO value, threshold, confidence, allowlist result, cooldown result, verdict, and reason
  5. An approved rollback calls the deployer sidecar, waits for recovery, and issues a post-action verification query that confirms recovery; a denial produces an evidence-linked human recommendation instead of acting
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Law 3 — Self-Observability, Loop Breaker, Cost Watchdog, Dashboard
**Goal**: Agent K can halt its own in-flight investigation when it loops or overspends — not merely log the fact afterward — and every signal from every prior phase converges onto one reviewable dashboard.
**Depends on**: Phase 3 (instrumentation), Phase 5 (policy spans to display)
**Requirements**: LAW3-01, LAW3-02, LAW3-03, LAW3-04, LAW3-05, LAW3-06, REPT-01, REPT-02, REPT-03
**Success Criteria** (what must be TRUE):
  1. Forcing repeated identical MCP queries in a test run causes the loop breaker to halt the investigation, fire a watchdog alert, mark the investigation incomplete, and escalate with evidence collected so far
  2. Forcing the configured cost/token budget to be exceeded in a test run halts the investigation with a "could not safely complete within budget" report, rather than continuing silently
  3. A run with deliberately missing LLM usage data surfaces as an error in the report, never recorded as zero cost; retried calls are visibly tracked separately from billed calls in both cost totals and loop-breaker repetition counts
  4. Each investigation renders a versioned Markdown report with evidence links and the same structured RCA recorded as SigNoz span events/attributes
  5. The single SigNoz dashboard shows all four sections (service health, incident context, agent health, action audit trail) with no unbounded-ID metric labels (cardinality reviewed)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
**UI hint**: yes

### Phase 7: Eval, Clean-Machine Rebuild, Demo, Submission
**Goal**: The full system is proven against the locked evaluation targets, a second independently-timed clean-machine rebuild confirms reproducibility, and the project is packaged honestly for judges.
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, EVAL-08
**Success Criteria** (what must be TRUE):
  1. Each of the four seeded incidents has been run three times with diagnosis accuracy, cost, and time-to-diagnosis recorded for every run, and diagnosis accuracy is 4/4 correct top-level diagnoses across the seeded scenarios (reported as "4/4 on four controlled scenarios," never as general accuracy)
  2. 100% of rendered evidence links resolve across the full eval matrix (link checker run against every report, not just Phase 4's smoke test)
  3. Zero actions execute outside the policy gate across all runs, confirmed by auditing every action span against a corresponding policy-verdict span
  4. A second, independently-timed clean-machine Foundry rebuild completes in under 15 minutes
  5. The two rollback scenarios (Incidents 1 and 2) are compared against a scripted manual baseline, and the submission blog (written from the actual build log, including any failed/confusing runs) discloses AI-assistant usage; demo footage and screenshots follow the locked demo script end to end; `casting.yaml` and `casting.yaml.lock` are committed
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — SigNoz, App, Telemetry, Sidecar Skeleton | 0/TBD | Not started | - |
| 2. SLOs, Alerts, Deployment Markers, Seeded Incidents | 0/TBD | Not started | - |
| 3. Agent Core — State Machine, MCP, RCA Schema, Full LLM Instrumentation | 0/TBD | Not started | - |
| 4. Law 1 — Evidence Validator and Link Checker | 0/TBD | Not started | - |
| 5. Law 2 — Policy Gate and Rollback Wiring | 0/TBD | Not started | - |
| 6. Law 3 — Self-Observability, Loop Breaker, Cost Watchdog, Dashboard | 0/TBD | Not started | - |
| 7. Eval, Clean-Machine Rebuild, Demo, Submission | 0/TBD | Not started | - |
</content>
