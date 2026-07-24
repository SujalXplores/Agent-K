# Requirements: Agent K

**Defined:** 2026-07-20
**Core Value:** Every claim Agent K publishes is backed by resolvable SigNoz evidence, and every action it takes passes a code-enforced safety gate — nothing is trust-the-model, everything is prove-it-in-telemetry.

## v1 Requirements

Requirements for the hackathon submission (locked scope — no additions unless an existing item is removed first). Each maps to roadmap phases.

### Telemetry Foundation (TELE)

- [x] **TELE-01**: SigNoz runs self-hosted via Foundry, with `casting.yaml` and `casting.yaml.lock` committed to the repo
- [x] **TELE-02**: A clean-machine Foundry rebuild (fresh clone → running SigNoz) completes in under 15 minutes, measured and recorded, not assumed
- [x] **TELE-03**: A minimal FastAPI skeleton emits traces, metrics, and logs that are confirmed visible in the SigNoz UI, with a console-exporter fallback available for debugging when telemetry doesn't arrive

### RAG Service (RAG)

- [ ] **RAG-01**: A FastAPI `/ask` endpoint answers a support question by retrieving relevant docs from pgvector and generating an answer via the configured LLM provider
- [x] **RAG-02**: A synthetic support-doc corpus (50-200 authored docs) is seeded into PostgreSQL+pgvector using local `sentence-transformers` embeddings (no external embedding API)
- [ ] **RAG-03**: Every LLM call in the RAG service (retrieval, prompt-construction, answer-generation steps) is instrumented with OpenTelemetry traces carrying GenAI semantic-convention attributes
- [ ] **RAG-04**: The LLM client is a single OpenAI-compatible module that switches between Groq, Cerebras, and Gemini Flash via an environment variable, optionally routed through LiteLLM

### Failure Injection (FLAG)

- [ ] **FLAG-01**: An in-process feature-flag service (admin HTTP endpoint / in-memory store) toggles each of the four seeded failure scenarios live, without restarting the app
- [ ] **FLAG-02**: Toggling the prompt-regression scenario ships a broken prompt template and produces a rising failed-answer rate with a corresponding SigNoz deployment marker
- [ ] **FLAG-03**: Toggling the retry-storm scenario lowers timeouts and causes repeated LLM calls, spiking cost/call-rate metrics past the configured cost SLO without necessarily raising HTTP error rate
- [ ] **FLAG-04**: Toggling the retrieval-latency scenario injects artificial delay into the pgvector retrieval query, visibly slowing retrieval spans in the trace waterfall with no deployment-related cause
- [ ] **FLAG-05**: Toggling the DB-pool-exhaustion scenario reduces configured DB connections, producing connection-pool-exhaustion errors in logs correlated to failed traces
- [ ] **FLAG-06**: A SigNoz deployment marker is created for every version change, including flag-triggered "deployments" (scenarios 1 and 2), and is distinguishable from non-deployment flag toggles (scenarios 3 and 4)

### Dashboard & Alerts (DASH)

- [ ] **DASH-01**: One SigNoz dashboard, hand-built in the SigNoz UI and exported as JSON into the repo, contains a Service Health section (request rate, error rate, latency, retrieval latency, LLM latency, SLO status, burn rate, current deployment version)
- [ ] **DASH-02**: The dashboard's Incident Context section shows active alerts, deployment markers, incident start time, affected service, related trace IDs, and links to relevant traces/logs/metrics
- [ ] **DASH-03**: The dashboard's Agent Health section shows cost per investigation, token usage, investigation duration, MCP query count, query failures, repeated-query count, hypothesis confidence, and watchdog alerts
- [ ] **DASH-04**: The dashboard's Action Audit Trail section shows proposed action, policy checks, SLO/confidence values, allow/deny verdict, execution time, and verification result — with denied verdicts given equal visual prominence to approved ones
- [ ] **DASH-05**: Service SLOs and burn-rate/cost alert rules are hand-built in the SigNoz UI, configured separately from the dashboard, and wired to fire a webhook to Agent K when breached

### SigNoz MCP Integration (MCP)

- [ ] **MCP-01**: Agent K's Python process connects to the SigNoz MCP server via the official MCP Python SDK and successfully retrieves real evidence (a trace, log, or metric query result) end-to-end
- [ ] **MCP-02**: Every MCP query Agent K issues routes through a single call-site wrapper that records the query as a span and hashes it for loop detection

### Investigation Core (INV)

- [ ] **INV-01**: Agent K receives a SigNoz alert via a webhook HTTP endpoint and starts an investigation in response
- [ ] **INV-02**: Agent K's investigation is driven by a plain Python state machine (no agent framework) that queries SigNoz via MCP, forms one or more root-cause hypotheses, and reaches a terminal reported/escalated state
- [ ] **INV-03**: Agent K attempts each of the four seeded incidents and produces at least one root-cause hypothesis per incident

### Law 1 — Evidence (LAW1)

- [ ] **LAW1-01**: Every published claim carries claim text, a confidence value, the SigNoz query used, the time range searched, and a resolvable evidence link (trace/log/metric/deployment)
- [ ] **LAW1-02**: The report renderer strips any claim with an empty evidence list before it's shown — Agent K cannot publish an unsupported claim
- [ ] **LAW1-03**: Confidence on each claim is hybrid-scored: the LLM proposes an initial value, then code recalibrates it based on evidence strength/count (deployment marker present, error-rate delta magnitude, etc.)
- [ ] **LAW1-04**: Agent K creates span links between its investigation spans and the original incident traces, so a human can navigate from failure to agent reasoning in one click
- [ ] **LAW1-05**: An automated link checker run during evaluation confirms 100% of rendered evidence links resolve against the running SigNoz instance

### Law 2 — Action Policy (LAW2)

- [ ] **LAW2-01**: A code-based policy module checks SLO/burn-rate breach, allowlist membership, cooldown period, confidence threshold, deployment-related cause, and sandbox scope before any action — with zero LLM involvement in the allow/deny decision
- [ ] **LAW2-02**: The action allowlist contains exactly one action: rollback to the previous application version
- [ ] **LAW2-03**: A separate, dependency-light `deployer` sidecar is the sole holder of the Docker socket and exposes exactly one authenticated endpoint (`POST /rollback`) — Agent K never holds the Docker socket; when a rollback is approved, Agent K makes one authenticated HTTP call to that endpoint carrying no image reference (the sidecar itself determines the previous known-good tag), and the sidecar runs `docker compose up -d --force-recreate` (never `restart`) after capturing the pre-mutation image tag, guarded by a concurrency lock (returns 409 if a rollback is already in flight)
- [ ] **LAW2-04**: On rollback the deployer sidecar creates a SigNoz deployment marker; Agent K then waits, re-queries SigNoz to verify recovery, and records the verified outcome
- [ ] **LAW2-05**: When any safety check fails, Agent K takes no action and instead produces an evidence-linked recommendation for a human
- [ ] **LAW2-06**: Every policy decision (requested action, incident ID, SLO value, threshold, confidence, allowlist result, cooldown result, final verdict, reason) is recorded as a telemetry span
- [ ] **LAW2-07**: Across the four seeded incidents, exactly two produce an approved rollback (prompt-regression, retry-storm) and two produce a denied verdict (retrieval-latency, DB-pool-exhaustion)

### Law 3 — Self-Telemetry (LAW3)

- [ ] **LAW3-01**: Every LLM call Agent K makes records input/output token counts and estimated cost as telemetry
- [ ] **LAW3-02**: Investigation duration, MCP query count, query failures, and repeated-query count are recorded per investigation
- [ ] **LAW3-03**: Hypothesis count and confidence per hypothesis are recorded per investigation
- [ ] **LAW3-04**: The loop breaker hashes each MCP query, stops the investigation when the same query repeats past a configured threshold, records the loop event, fires a watchdog alert, marks the investigation incomplete, and escalates to a human with evidence collected so far
- [ ] **LAW3-05**: The cost watchdog stops the investigation and reports incompletion if token/cost usage exceeds a configured budget mid-investigation
- [ ] **LAW3-06**: At least one adversarial test forces the loop breaker to actually fire (not just exist unexercised in code)

### Incident Report (REPT)

- [ ] **REPT-01**: A small FastAPI-served HTML report page renders a completed investigation's structured RCA (claims, evidence, policy verdict, verification result) with clickable SigNoz deep links
- [ ] **REPT-02**: The report page is addressable by incident ID (`/report/{id}`) and a simple index/list view lets a human browse past investigations, not only the latest one
- [ ] **REPT-03**: An investigation that hits the loop breaker or cost watchdog renders in the report/dashboard as an explicit incomplete/needs-human state (passive escalation — no notification channel is built)

### Evaluation Harness (EVAL)

- [ ] **EVAL-01**: Each of the four seeded incidents runs 3 times, recording diagnosis correctness, investigation cost, time-to-diagnosis, and rollback result per run
- [ ] **EVAL-02**: The evaluation harness paces/backs off LLM calls to stay within Groq free-tier rate limits across all 12 runs, with the Cerebras overflow path proven working before the final eval
- [ ] **EVAL-03**: The two rollback scenarios are compared against a scripted manual baseline (time/steps for a human to reach the same diagnosis/action)
- [ ] **EVAL-04**: Results are reported honestly in the submission blog, including any failed or confusing runs, without inflating claims beyond "4/4 on four controlled scenarios"

### Submission (SUB)

- [ ] **SUB-01**: AI assistant usage (Claude Code) is disclosed in the final submission per hackathon rules
- [ ] **SUB-02**: The submission blog is written from the actual build log and includes screenshots/demo footage covering the 15-beat demo script

## v2 Requirements

None — scope is fully locked for this hackathon milestone; there is no deferred backlog. Anything not in v1 above is in Out of Scope below, permanently for this milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-channel notifications (Slack, Jira, ServiceNow paging) | Zero-budget + 7-day constraint; the HTML report + SigNoz dashboard is the interface, no judging-criteria payoff for chat-ops polish |
| Alert correlation/dedup/grouping across many concurrent alerts | Agent K has exactly 4 seeded incident types firing one at a time; no noise-reduction problem exists in this scope |
| Expanded remediation action catalog beyond the one rollback action | The single-allowlisted-action constraint is the entire point of Law 2's safety story; more actions multiply attack surface for a team with zero prior DevOps experience |
| Fully autonomous "no human ever" remediation | Undermines the safety-first pitch and the honesty commitment; every action stays gated behind Law 2, no exceptions |
| General-purpose chat/Q&A interface over telemetry | Explicit anti-goal — Agent K is an evidence-producing workflow, not a chatbot; a chat box would blur that positioning |
| Cross-service/dependency-graph root-causing | Agent K is a single FastAPI app with one datastore; no dependency graph exists to trace, and building one requires infra (K8s/service mesh) that's out of scope |
| Kubernetes, worker/queue systems, microservices beyond the single FastAPI app | Deliberately kept simple to finish in 7 days |
| Any paid LLM APIs or paid infra in the shipped product's runtime | Zero-budget constraint — Claude Code subscription is build-time only, never shipped |
| Dashboard-as-code / programmatic alert provisioning | Hand-built in SigNoz UI instead — faster to build, matches "deepest SigNoz integration" judging criterion equally well |
| Agent orchestration frameworks (LangGraph, PydanticAI, etc.) | Plain Python state machine chosen for full control over Law enforcement; team has zero prior agent-framework experience |
| Real/production support data or PII | Synthetic authored corpus only — avoids licensing/privacy concerns |
| Active human paging/notification on escalation | Passive-only (report/dashboard reflects incomplete state) — no notification channel budget or time in 7 days |
| Docker socket mounted into Agent K | Grants effective host root and undercuts the "sandboxed single-action" Law 2 claim; the `deployer` sidecar is the sole Docker-socket holder and Agent K reaches it only via one authenticated HTTP call |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TELE-01 | Phase 1 | Complete |
| TELE-02 | Phase 1 | Complete |
| TELE-03 | Phase 1 | Complete |
| RAG-01 | Phase 2 | Reopened |
| RAG-02 | Phase 2 | Complete |
| RAG-03 | Phase 2 | Reopened |
| RAG-04 | Phase 2 | Needs human verification |
| FLAG-01 | Phase 3 | Pending |
| FLAG-02 | Phase 3 | Pending |
| FLAG-03 | Phase 3 | Pending |
| FLAG-04 | Phase 3 | Pending |
| FLAG-05 | Phase 3 | Pending |
| FLAG-06 | Phase 3 | Pending |
| DASH-01 | Phase 3 | Pending |
| DASH-02 | Phase 3 | Pending |
| DASH-03 | Phase 7 | Pending |
| DASH-04 | Phase 7 | Pending |
| DASH-05 | Phase 3 | Pending |
| MCP-01 | Phase 4 | Pending |
| MCP-02 | Phase 4 | Pending |
| INV-01 | Phase 5 | Pending |
| INV-02 | Phase 5 | Pending |
| INV-03 | Phase 5 | Pending |
| LAW1-01 | Phase 5 | Pending |
| LAW1-02 | Phase 5 | Pending |
| LAW1-03 | Phase 5 | Pending |
| LAW1-04 | Phase 5 | Pending |
| LAW1-05 | Phase 5 | Pending |
| LAW2-01 | Phase 6 | Pending |
| LAW2-02 | Phase 6 | Pending |
| LAW2-03 | Phase 6 | Pending |
| LAW2-04 | Phase 6 | Pending |
| LAW2-05 | Phase 6 | Pending |
| LAW2-06 | Phase 6 | Pending |
| LAW2-07 | Phase 6 | Pending |
| LAW3-01 | Phase 5 | Pending |
| LAW3-02 | Phase 5 | Pending |
| LAW3-03 | Phase 5 | Pending |
| LAW3-04 | Phase 5 | Pending |
| LAW3-05 | Phase 5 | Pending |
| LAW3-06 | Phase 5 | Pending |
| REPT-01 | Phase 7 | Pending |
| REPT-02 | Phase 7 | Pending |
| REPT-03 | Phase 7 | Pending |
| EVAL-01 | Phase 7 | Pending |
| EVAL-02 | Phase 7 | Pending |
| EVAL-03 | Phase 7 | Pending |
| EVAL-04 | Phase 7 | Pending |
| SUB-01 | Phase 7 | Pending |
| SUB-02 | Phase 7 | Pending |

**Coverage:**

- v1 requirements: 50 total (corrected from an initial miscount of 51 during requirements definition; verified by direct enumeration during roadmap creation)
- Mapped to phases: 50/50 ✓
- Unmapped: 0 ✓

**Reopened requirements** (2026-07-24, see `.planning/phases/02-rag-service-core/02-VERIFICATION.md`):

- RAG-01 and RAG-03 were reopened because `POST /ask` returned HTTP 500 against the live database and only one of the three required GenAI spans was emitted. Gap-closure plans 02-05/02-06 have since fixed the pgvector adapter conflict and wired `setup_db_instrumentation()` — verified live: `POST /ask` returns 200 with grounded sources, and `scripts/probe_ask_spans.py` proves all three GenAI spans plus the SQLAlchemy `SELECT` span are emitted on a real request (25/25 tests passing, including 3 live-DB integration tests). They close again only on a passing re-verification of Phase 2 — not merely by the gap-closure plans landing.
- RAG-04 was moved to needs-human-verification because no provider credential exists in this environment, so no live third-party call could be made. Client construction is proven for all three providers, and 02-07's `MissingProviderKeyError` guard now fails fast on a missing/empty key instead of leaking an ambient `OPENAI_API_KEY`. It closes when a human performs **HV-1**, the provider-switch check defined in `.planning/phases/02-rag-service-core/02-07-PLAN.md`.

---
*Requirements defined: 2026-07-20*
*Last updated: 2026-07-24 — RAG-01/RAG-03 reopened and RAG-04 moved to needs-human-verification per 02-VERIFICATION.md, gap-closure applied (02-05..02-07). Roadmap-creation update: 2026-07-20 (traceability populated, requirement count corrected 51->50).*
