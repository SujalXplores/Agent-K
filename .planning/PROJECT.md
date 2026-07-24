# Agent K

## What This Is

Agent K is a code-enforced incident-response agent for a FastAPI RAG support-answering service, built for the "Agents of SigNoz" hackathon (Track 01 — AI & Agent Observability, July 20–26, 2026). When a SigNoz alert fires, Agent K investigates via the SigNoz MCP server, publishes only evidence-backed root-cause claims, executes a sandboxed rollback only when a code-based policy allows it, and records its own cost/behavior as telemetry so every decision is auditable in SigNoz.

## Core Value

Every claim Agent K publishes is backed by resolvable SigNoz evidence, and every action it takes passes a code-enforced safety gate — nothing is trust-the-model, everything is prove-it-in-telemetry.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] FastAPI RAG support-answering service: PostgreSQL+pgvector (single datastore for support data + vectors), one LLM provider, retrieval step, prompt-construction step, answer-generation step, full OTel instrumentation (traces/metrics/logs + GenAI semconv attributes) → SigNoz
- [ ] Synthetic support-doc corpus (~50-200 authored docs) seeded into pgvector
- [ ] Four seeded failure scenarios, toggled live via an in-process feature-flag service (admin HTTP endpoint / in-memory store, no restart needed): prompt-regression deployment, retry-storm cost runaway, retrieval latency injection, DB pool exhaustion
- [ ] Deployment markers in SigNoz for every version change (including flag-triggered "deployments")
- [ ] Service SLOs + burn-rate/cost alerts, hand-built in SigNoz UI, wired to fire a webhook to Agent K
- [ ] Agent K core: plain Python state machine (no agent framework) driving the investigation loop
- [ ] Agent K ↔ SigNoz MCP integration via the official MCP Python SDK, called directly from the state machine (every query individually visible for Law 1/3 telemetry)
- [ ] Law 1 (no claim without evidence): structured claim schema (claim, confidence, evidence[] with type/query/time_range/link), report renderer strips claims with empty evidence, span links from investigation spans to incident traces, automated link checker validating every evidence link resolves against the running SigNoz instance
- [ ] Confidence scoring: hybrid — LLM proposes an initial confidence, code recalibrates it based on evidence strength/count (deployment marker present, error-rate delta magnitude, etc.)
- [ ] Law 2 (no action without budget): code-based policy module checking SLO/burn-rate breach, allowlist membership, cooldown, confidence threshold, deployment-related cause, sandbox scope — allowlist contains exactly one action (rollback to previous version)
- [ ] Rollback executor + deployer sidecar: a separate, dependency-light `deployer` sidecar is the sole holder of the Docker socket, exposing exactly one authenticated `POST /rollback` endpoint that rolls the app back to its previous known-good image tag (`docker compose up -d --force-recreate`, never `restart`), holds a concurrency lock, and emits a SigNoz deployment marker at rollback time. Agent K never holds the Docker socket — its `act` stage makes one authenticated HTTP call carrying no image reference, then waits and re-queries SigNoz to verify recovery and records the outcome
- [ ] Law 3 (no self without telemetry): every LLM call, token counts, estimated cost, investigation duration, MCP query count/failures/repeats, hypothesis count/confidence, policy decisions, actions attempted/approved/denied, verification results — all recorded as spans/metrics in SigNoz
- [ ] Loop breaker: hashes each MCP query, stops investigation on excessive repeats, records the loop event, fires a watchdog alert, marks investigation incomplete, escalates to human with partial evidence
- [ ] Cost watchdog: stops investigation and reports incompletion if token/cost budget is exceeded mid-investigation
- [ ] Structured incident report: small FastAPI-served HTML report page rendering the JSON RCA report with clickable SigNoz deep links (not just raw JSON/log data)
- [ ] One polished SigNoz dashboard (hand-built in SigNoz UI, exported as JSON for the repo), four sections: service health, incident context, agent health, action audit trail
- [ ] Alerts configured separately from the dashboard (same hand-built-in-UI approach)
- [ ] Foundry deployment: `casting.yaml` + `casting.yaml.lock` committed, clean-machine rebuild target < 15 min
- [ ] LLM provider abstraction: single OpenAI-compatible client module behind an env-var-selected provider (Groq primary — `llama-3.1-8b-instant` for RAG app, `llama-3.3-70b-versatile` for Agent K reasoning; Cerebras as eval-day overflow; Gemini Flash free tier as tool-calling fallback), optionally routed through LiteLLM
- [ ] Local embeddings via `sentence-transformers` (no external embedding API)
- [ ] Evaluation harness: 3 runs per incident, tracks diagnosis accuracy, evidence-link resolution rate, actions-outside-policy count, rollback approve/deny counts, cost/duration, loop-breaker firing, manual-baseline comparison
- [ ] Submission blog written from the actual build log, results reported honestly including any failed/confusing runs

### Out of Scope

- General-purpose chatbot UI or a dashboard-with-chat-box framing — Agent K is an evidence-producing workflow, not a Q&A bot (explicit anti-goal in spec)
- Unsupervised production remediation beyond the single allowlisted rollback action — safety-first constraint, only one action is ever permitted
- Kubernetes, worker/queue systems, microservices beyond the single FastAPI app — deliberately kept simple to finish in 7 days
- Any paid LLM APIs or paid infra in the shipped product's runtime — zero-budget constraint (Claude Code subscription is build-time only, not shipped)
- Dashboard-as-code / programmatic alert provisioning — hand-built in SigNoz UI instead, matches "deepest SigNoz integration" judging criterion and is faster to build
- Agent orchestration frameworks (LangGraph, PydanticAI, etc.) — plain Python state machine chosen for full control over Law enforcement and because the team has zero prior agent-framework experience
- Real/production support data or PII — synthetic authored corpus only, avoids licensing/privacy concerns
- Claiming general production readiness from the four test scenarios — results reported strictly as "4/4 on four controlled scenarios"

## Context

- Hackathon: "Agents of SigNoz" (WeMakeDevs × SigNoz), July 20–26, 2026, Track 01 (AI & Agent Observability). Prize: one MacBook Air per team member for top submissions + possible SigNoz interviews (no offer guarantee).
- Team: 4 members, majority web-tech background, **zero prior Docker/DevOps/OpenTelemetry experience** — onboarding/ramp-up must be planned for, not assumed away.
- One team member unavailable July 24–26 (days 5-7 of the build window) — plan accordingly; role assignment is deliberately left to the team day-of rather than fixed in the plan.
- AI assistant use (Claude Code) is permitted in the hackathon but **must be disclosed** in the final submission — failure to disclose = disqualification.
- Judging weighs 6 criteria equally-ish: potential impact, creativity, technical excellence, best use of SigNoz, UX, presentation quality.
- SigNoz field requirements are mandatory and judged directly: install via Foundry, use MCP server + Query Builder + dashboards + alerts, repo must include `casting.yaml`/`casting.yaml.lock` for judge reproduction.
- Warm-up blog side-prize already completed (self-hosted SigNoz write-up submitted solo before July 19).
- A one-page infographic exists as visual reference for dashboard/report UI styling only — its sample numbers are illustrative, not targets (real targets are in Requirements/evaluation section below).
- Repo layout: single monorepo containing the monitored app, Agent K, and infra config (`casting.yaml` etc.) — simplest for judge review and a 7-day build.

## Constraints

- **Timeline**: Locked 7-day build window, July 20–26, 2026 — the day-by-day plan in the roadmap must map onto this exactly (see locked build plan below).
- **Budget**: Zero-budget shipped runtime — only free tiers / open-source / self-hosted. Only the Claude Code subscription (build-time tool) is paid.
- **Team skill**: No prior Docker/OTel/SigNoz experience on the team — plan must include ramp-up time, not assume fluency.
- **Team availability**: One of 4 members unavailable July 24–26 — later-phase work (Law 2/3, dashboard, eval day) has reduced capacity.
- **LLM provider**: Locked to Groq (primary) / Cerebras (overflow) / Gemini Flash (fallback) behind one OpenAI-compatible client, provider chosen via env var, optional LiteLLM routing. Embeddings are local `sentence-transformers` only.
- **Scope lock**: No additions to locked scope (section 3 of source spec) unless an existing feature is removed first — prevents hackathon scope creep.
- **Evidence integrity**: Every published claim must carry a resolvable SigNoz evidence link; a link checker run during evaluation must confirm 100% resolve.
- **Action safety**: The rollback allowlist contains exactly one action; zero actions may execute outside the Law 2 policy gate.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Alert trigger = SigNoz webhook → Agent K HTTP endpoint | Real event-driven path, demoable live, matches how SigNoz alerting actually integrates | — Pending |
| Agent loop = plain Python state machine, no framework | Full control over Law enforcement; team has zero agent-framework experience; avoids framework lock-in risk in a 7-day window | — Pending |
| Incident report = small FastAPI-served HTML report page | Clean, low-cost demo surface beyond raw dashboard panels; still links out to SigNoz for evidence | — Pending |
| Rollback executes via a separate `deployer` sidecar exposing only `POST /rollback` | Agent K never holds the Docker socket, so Law 2's "inside the permitted sandbox" check is enforced by process isolation rather than convention — a compromised or misbehaving Agent K can at worst make one authenticated HTTP call to an endpoint that does exactly one hardcoded thing. This is the honest version of the safety claim and survives a judge probing it. | — Pending |
| Deployment markers are a custom OTel span (`deployment.marker`), emitted by the deployer sidecar at rollback time | SigNoz has no native deployment-marker API; a custom span is auditable and evidence-linkable like everything else Agent K produces, and emitting it from the sidecar keeps the marker on the same component that performed the mutation | — Pending |
| RAG corpus = synthetic authored docs (~50-200) | No licensing/PII risk, fast to seed, full control over what failure scenarios need to surface | — Pending |
| Failure-flag seeding = in-process flag service (HTTP-toggleable, no restart) | Lets the demo script toggle scenarios live without conflating "flag toggle" with "deployment event" except where that conflation is deliberate (Incident 1/2) | — Pending |
| Confidence = hybrid (LLM proposes, code recalibrates) | Keeps Law 1 genuinely code-enforced rather than trusting a self-reported model number | — Pending |
| Repo layout = single monorepo | Simplest for a 7-day hackathon and for judges to review one place | — Pending |
| MCP wiring = direct official MCP Python SDK calls from the state machine | Every query individually visible/loggable for Law 1 evidence and Law 3 self-telemetry | — Pending |
| Dashboard + alerts hand-built in SigNoz UI (not dashboard-as-code) | Faster to build, matches "deepest SigNoz integration" judging criterion just as well, exported as JSON afterward for repo reproducibility | — Pending |
| Team role assignment left open (role-agnostic plan) | Avoids baking in assumptions about who's strongest where; team self-assigns day-of within the dependency-ordered roadmap | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-20 after initialization*
