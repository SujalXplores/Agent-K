# Roadmap: Agent K

## Overview

Agent K ships as a small set of coupled processes — the monitored RAG app, Agent K itself, and a minimal privilege-isolated `deployer` sidecar — built in dependency order across a locked 7-day window (Jul 20–26, 2026): first the observability substrate (SigNoz) and the monitored RAG app that will misbehave on cue, then the evidence pipeline (MCP) Agent K will query, then Agent K's own investigation loop with Law 1 (evidence) and Law 3 (self-telemetry) built in from the start, then the code-enforced Law 2 policy gate and the deployer sidecar that executes the single allowlisted rollback, and finally the report surface, dashboard polish, and the evaluation harness that proves all of it works across four seeded incidents. Each phase hands the next phase something it can query or act against — nothing in a later phase is buildable against mocks alone once its dependency phase is done.

**Timeline risk (flagged, not solved by phase ordering alone):** the team has zero prior Docker/OTel/SigNoz experience and one of four members is unavailable Jul 24–26 (days 5–7 of 7). A naive one-phase-per-day mapping would put the heaviest, most safety-critical phases (5, 6, 7 — 32 of 50 requirements, including both Laws 2 and 3 and the full eval harness) exactly in the reduced-capacity window. Plan-phase and execution should front-load Phase 5's Law 3 telemetry and Phase 6's policy-schema drafting as early as possible within their phases, and treat the Day 5–6 clean-machine-rebuild and Groq-rate-limit checkpoints (research-flagged) as hard go/no-go gates before Phase 7's eval runs, not day-of assumptions.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Telemetry Foundation** - Stand up self-hosted SigNoz via Foundry and confirm a minimal service's traces/metrics/logs actually arrive in the UI (completed 2026-07-23)
- [ ] **Phase 2: RAG Service Core** - Build the monitored `/ask` endpoint (pgvector retrieval + LLM generation) with full GenAI-instrumented OTel traces
- [ ] **Phase 3: Failure Injection + Dashboard + Alerting** - Wire the four toggleable failure scenarios, the Service Health/Incident Context dashboard sections, and SLO/burn-rate alerts that fire a webhook
- [ ] **Phase 4: SigNoz MCP Integration** - Give Agent K a single-call-site MCP client wrapper that retrieves real evidence from SigNoz
- [ ] **Phase 5: Agent K Core Loop** - Build the investigation state machine with Law 1 (evidence-backed claims) and Law 3 (self-telemetry, loop breaker, cost watchdog) instrumented inline
- [ ] **Phase 6: Policy Gate + Rollback Executor** - Build Law 2's zero-LLM policy gate and the single allowlisted, verified-outcome rollback action, executed through a privilege-isolated `deployer` sidecar (sole Docker-socket holder)
- [ ] **Phase 7: Report, Dashboard Polish & Evaluation** - Ship the HTML incident report, complete the Agent Health/Action Audit Trail dashboard sections, run the 12-run eval harness, and write the submission blog

## Phase Details

### Phase 1: Telemetry Foundation

**Goal**: The team has a working, reproducible SigNoz observability backend, and a minimal service's telemetry is confirmed visible in the SigNoz UI before any app logic is written.
**Depends on**: Nothing (first phase)
**Requirements**: TELE-01, TELE-02, TELE-03
**Success Criteria** (what must be TRUE):

  1. A fresh clone of the repo stands up SigNoz via Foundry (`casting.yaml`/`casting.yaml.lock`) on a clean machine, with the rebuild time measured and recorded as under 15 minutes.
  2. A minimal FastAPI skeleton service's traces, metrics, and logs are confirmed visible in the SigNoz UI.
  3. When OTLP telemetry doesn't arrive, a console-exporter fallback lets the team inspect spans locally to debug the pipeline.

**Plans**: 3/3 plans complete
**Wave 1**

- [x] 01-01-PLAN.md — FastAPI skeleton + OTel dual-exporter (console+OTLP-HTTP:4318) wiring [TELE-03 build]
- [x] 01-02-PLAN.md — SigNoz Foundry standup + committed casting.yaml/casting.yaml.lock + runbook [TELE-01]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — Rebuild-timing harness + end-to-end telemetry verification in SigNoz UI [TELE-02, TELE-03 verify]

### Phase 2: RAG Service Core

**Goal**: The monitored RAG application answers support questions end-to-end, with every step of the pipeline individually visible in SigNoz as GenAI-instrumented spans.
**Depends on**: Phase 1
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04
**Success Criteria** (what must be TRUE):

  1. A request to `POST /ask` returns a generated answer grounded in docs retrieved from pgvector.
  2. The pgvector store contains a seeded corpus of 50-200 synthetic support docs embedded locally via `sentence-transformers`, with no external embedding API called.
  3. Every `/ask` call produces distinct retrieval, prompt-construction, and generation spans in SigNoz carrying GenAI semantic-convention attributes.
  4. Switching the LLM provider env var (Groq / Cerebras / Gemini Flash) changes which provider serves requests with no code change.

**Plans**: 1/4 plans executed

**Wave 1**

- [ ] 02-01-PLAN.md — pgvector Postgres container + async SQLAlchemy engine + Document model + applied Alembic migration + local embedding module [RAG-01/02 substrate]
- [x] 02-03-PLAN.md — single OpenAI-compatible LLM client (env-var provider switch) + shared gen_ai telemetry helper [RAG-03/04]

**Wave 2** *(blocked on Wave 1)*

- [ ] 02-02-PLAN.md — synthetic 50-200 doc corpus + idempotent local-embedding seed into pgvector [RAG-02]

**Wave 3** *(blocked on 02-02 + 02-03)*

- [ ] 02-04-PLAN.md — POST /ask endpoint (retrieval + grounded prompt + generation, three GenAI spans, {answer, sources}) [RAG-01/03]

### Phase 3: Failure Injection + Dashboard + Alerting

**Goal**: Each of the four seeded failure scenarios can be toggled live and observed happening in SigNoz, and a threshold breach reliably fires a webhook Agent K can receive.
**Depends on**: Phase 2
**Requirements**: FLAG-01, FLAG-02, FLAG-03, FLAG-04, FLAG-05, FLAG-06, DASH-01, DASH-02, DASH-05
**Success Criteria** (what must be TRUE):

  1. An admin can toggle any of the four failure scenarios via an HTTP endpoint without restarting the app, and each toggle produces its documented symptom (broken prompt / retry storm / retrieval latency / DB-pool exhaustion) visible in SigNoz traces, metrics, or logs.
  2. Deployment-caused scenarios (prompt-regression, retry-storm) create a SigNoz deployment marker; non-deployment scenarios (retrieval-latency, DB-pool-exhaustion) do not — and the dashboard's Incident Context section reflects that distinction.
  3. The SigNoz dashboard's Service Health and Incident Context sections show live request rate, error rate, latency, SLO/burn-rate status, deployment version, active alerts, and related traces.
  4. When a configured SLO/burn-rate/cost alert breaches, SigNoz fires a webhook to a reachable HTTP endpoint, confirmed firing end-to-end.

**Plans**: TBD

### Phase 4: SigNoz MCP Integration

**Goal**: Agent K's Python process can retrieve real evidence from the running SigNoz instance through a single, loop-detection-ready call site — proven before any investigation logic is written against it.
**Depends on**: Phase 1 (needs SigNoz running); parallelizable with Phase 2-3, but must land before Phase 5
**Requirements**: MCP-01, MCP-02
**Success Criteria** (what must be TRUE):

  1. Agent K's process connects to the SigNoz MCP server via the official MCP Python SDK and a throwaway script retrieves a real trace, log, or metric query result end-to-end (not mocked).
  2. Every MCP query issued goes through one wrapper function, confirmed by seeing a span recorded and a query hash computed for each call made through it.

**Plans**: TBD

### Phase 5: Agent K Core Loop

**Goal**: Agent K receives a real SigNoz alert and runs its investigation state machine to a terminal state for each of the four seeded incidents, with every claim it could publish provably evidence-backed and every aspect of its own behavior — including guardrails that actually fire — recorded as telemetry.
**Depends on**: Phase 3, Phase 4
**Requirements**: INV-01, INV-02, INV-03, LAW1-01, LAW1-02, LAW1-03, LAW1-04, LAW1-05, LAW3-01, LAW3-02, LAW3-03, LAW3-04, LAW3-05, LAW3-06
**Success Criteria** (what must be TRUE):

  1. Posting a SigNoz alert webhook to Agent K's endpoint starts an investigation that runs the state machine to a terminal reported/escalated state, for each of the four seeded incidents, producing at least one root-cause hypothesis per incident.
  2. Every claim Agent K would publish carries claim text, a hybrid LLM-proposed/code-recalibrated confidence value, the SigNoz query used, the time range searched, and a resolvable evidence link — and any claim with an empty evidence list is stripped before it would be shown.
  3. A human can navigate from an incident trace to Agent K's investigation spans via a span link in one click, and an automated link checker confirms 100% of rendered evidence links resolve against the live SigNoz instance.
  4. Every investigation's LLM token counts/estimated cost, duration, MCP query count/failures/repeats, and hypothesis count/confidence are recorded as telemetry.
  5. An adversarial repeated-query test actually triggers the loop breaker (stops the investigation, fires a watchdog alert, marks it incomplete, escalates with partial evidence), and a separate forced-budget-overrun test actually triggers the cost watchdog — both observed firing, not just present in code.

**Plans**: TBD
**Constraint**: This is the highest-requirement-count phase (14 reqs) and should be substantially complete before the team-availability gap (Jul 24-26) begins, since Phase 6's policy gate is a hard dependency on its evidence/confidence schema.

### Phase 6: Policy Gate + Rollback Executor

**Goal**: Every action Agent K could take passes through a deterministic, zero-LLM policy gate, and the one allowlisted rollback action executes through a privilege-isolated `deployer` sidecar only when policy allows it, with the outcome independently re-verified against SigNoz.
**Depends on**: Phase 5
**Requirements**: LAW2-01, LAW2-02, LAW2-03, LAW2-04, LAW2-05, LAW2-06, LAW2-07
**Success Criteria** (what must be TRUE):

  1. The policy module's allow/deny verdict for each incident is produced entirely by code (zero LLM calls in the decision), checking SLO/burn-rate breach, allowlist membership, cooldown, confidence threshold, deployment-relatedness, and sandbox scope.
  2. The action allowlist contains exactly one action (rollback), and across the four seeded incidents exactly two (prompt-regression, retry-storm) produce an approved rollback and two (retrieval-latency, DB-pool-exhaustion) produce a denied verdict.
  3. When any safety check fails, Agent K takes no action and instead produces an evidence-linked recommendation for a human.
  4. A `deployer` sidecar is the sole holder of the Docker socket and exposes exactly one authenticated `POST /rollback` endpoint; Agent K never holds the socket. On an approved rollback Agent K makes one authenticated HTTP call carrying no image reference, the sidecar captures the pre-mutation image tag, runs `docker compose up -d --force-recreate` (never `restart`) under a concurrency lock, and creates a SigNoz deployment marker; Agent K then re-queries SigNoz to confirm recovery before recording the verified outcome.
  5. Every policy decision (requested action, incident ID, SLO value, threshold, confidence, allowlist result, cooldown result, final verdict, reason) is recorded as a telemetry span.

**Plans**: TBD
**Constraint**: Safety-critical phase (the `deployer` sidecar holds the Docker socket and mutates the monitored app's running config) landing inside or just before the team-availability gap (Jul 24-26) — the sidecar isolation boundary and policy schema should be settled early, not debugged with reduced headcount. The sidecar has no dependency on Agent K's reasoning pipeline (only on the app + versioned images existing), so its skeleton (container, socket mount, one hardcoded authenticated endpoint, concurrency lock) can be scaffolded and smoke-tested well before this phase to de-risk it.

### Phase 7: Report, Dashboard Polish & Evaluation

**Goal**: A human can browse any past investigation as a readable RCA report with working evidence links, Agent K's own health and every action decision are reflected in the SigNoz dashboard, and the team has run and honestly reported a repeatable evaluation across all four incidents.
**Depends on**: Phase 6
**Requirements**: REPT-01, REPT-02, REPT-03, DASH-03, DASH-04, EVAL-01, EVAL-02, EVAL-03, EVAL-04, SUB-01, SUB-02
**Success Criteria** (what must be TRUE):

  1. A human can open `/report/{id}` for any past investigation and see its claims, evidence, policy verdict, and verification result rendered as HTML with clickable SigNoz deep links, and browse all past investigations from an index/list view.
  2. An investigation that hit the loop breaker or cost watchdog renders in the report/dashboard as an explicit incomplete/needs-human state.
  3. The SigNoz dashboard's Agent Health and Action Audit Trail sections show real data — cost/tokens/duration/MCP query stats/hypothesis confidence/watchdog alerts, and proposed actions with policy checks and verdicts, with denied verdicts as visually prominent as approved ones.
  4. Each of the four seeded incidents has been run 3 times (12 runs total) with diagnosis correctness, cost, time-to-diagnosis, and rollback result recorded per run, staying within Groq free-tier rate limits with a proven-working Cerebras overflow path.
  5. The two rollback scenarios have a scripted manual-baseline comparison, and the submission blog reports all of this honestly (including any failed/confusing runs) with AI-assistant usage disclosed and demo-script screenshots/footage included.

**Plans**: TBD
**Constraint**: Falls entirely within the team-availability gap (Jul 24-26) and is timeline-sensitive by nature (12 paced eval runs + blog writing) — the Day 5-6 clean-machine-rebuild and Groq-rate-limit checkpoints (research-flagged) must be validated before this phase's eval runs start, with room to cut scope (smaller embedding model, pre-baked corpus) if either fails.
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Telemetry Foundation | 3/3 | Complete   | 2026-07-23 |
| 2. RAG Service Core | 1/4 | In Progress|  |
| 3. Failure Injection + Dashboard + Alerting | 0/TBD | Not started | - |
| 4. SigNoz MCP Integration | 0/TBD | Not started | - |
| 5. Agent K Core Loop | 0/TBD | Not started | - |
| 6. Policy Gate + Rollback Executor | 0/TBD | Not started | - |
| 7. Report, Dashboard Polish & Evaluation | 0/TBD | Not started | - |
