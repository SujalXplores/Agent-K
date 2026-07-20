# Agent K — The Evidence-First Incident Agent

## What This Is

Agent K is a code-enforced incident-response agent that investigates failures in an AI application using SigNoz, publishes only evidence-backed conclusions, takes action only when strict safety rules allow it, and records its own behavior so humans can audit everything it did.

It is not a chatbot with a dashboard. It is an evidence-producing incident workflow with an AI investigator inside it, built for the **Agents of SigNoz** hackathon (Track 01: AI & Agent Observability) by WeMakeDevs and SigNoz.

The audience is an engineer who would otherwise spend an hour hand-searching traces, metrics, logs, and deployment history to understand why an AI service went slow, expensive, wrong, or stuck — and who does not trust an autonomous agent near production.

## Core Value

**Every conclusion Agent K publishes is traceable to SigNoz evidence, and every action it takes has passed a code-enforced policy gate.**

If the investigation is slow, if the report is ugly, if only one incident type works — those are survivable. If Agent K publishes a claim it cannot prove, or takes an action the policy did not authorize, the project has failed at its only real thesis.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

**Monitored application**

- [ ] A FastAPI RAG support-answering service that produces realistic AI-application telemetry
- [ ] PostgreSQL + pgvector as the single datastore for both support data and vector retrieval
- [ ] OpenTelemetry traces, metrics, and structured logs shipped to SigNoz
- [ ] GenAI semantic-convention attributes on all model calls

**Law 1 — No claim without evidence**

- [ ] Structured RCA claim schema (claim, confidence, evidence[], query, time range, link, relationship)
- [ ] Evidence validator that strips any claim with an empty evidence list before rendering
- [ ] SigNoz deep-link generation for every piece of evidence
- [ ] Automated link checker verifying every rendered link resolves against the running SigNoz instance
- [ ] Span links connecting investigation spans to the original incident traces

**Law 2 — No action without budget**

- [ ] Code-based policy module gating every action on six checks (SLO breach, allowlist, cooldown, confidence, deployment-related cause, sandbox)
- [ ] A single-entry action allowlist: rollback to previous application version
- [ ] Rollback executor with post-action verification query
- [ ] Every policy verdict emitted as a telemetry span with full decision inputs and reason
- [ ] Evidence-linked human recommendation produced whenever a check fails

**Law 3 — No self without telemetry**

- [ ] Per-LLM-call instrumentation: token counts, computed cost, duration
- [ ] Investigation-level metrics: duration, MCP query count, query failures, repeated queries, hypothesis count and confidence
- [ ] Loop breaker that hashes MCP queries and halts on excessive repetition, firing a watchdog alert and escalating
- [ ] Cost watchdog that halts investigation when the configured budget is exceeded

**Incidents and evaluation**

- [ ] Four seeded, flag-controlled incidents: prompt regression, retry-storm cost runaway, retrieval latency injection, database pool exhaustion
- [ ] Two expected rollback approvals (incidents 1, 2) and two expected denials (incidents 3, 4)
- [ ] Three runs of each incident with recorded diagnosis accuracy, cost, and time to diagnosis
- [ ] Scripted manual baseline for comparison on the two rollback scenarios

**Observability surface**

- [ ] One SigNoz dashboard with four sections: service health, incident context, agent health, action audit trail
- [ ] SigNoz alerts configured separately from the dashboard
- [ ] SigNoz MCP server as the investigation data path
- [ ] Foundry deployment with committed `casting.yaml` and `casting.yaml.lock`

**Submission**

- [ ] Clean-machine Foundry rebuild completing in under 15 minutes
- [ ] Demo footage and screenshots following the locked demo script
- [ ] Submission blog written from the actual build log, including failed and confusing runs
- [ ] AI assistance disclosed (mandatory — non-disclosure is disqualifying)

### Out of Scope

- **Kubernetes, worker systems, message queues, extra microservices** — the project must be small enough to finish in seven days and reliable enough to demo live
- **A general-purpose chatbot or a dashboard with a chat box** — Agent K is a workflow, not a conversational surface
- **Unsupervised production remediation** — one sandboxed action only, behind a policy gate
- **A generic LLM cost tracker** — cost telemetry exists to serve the safety policy, not as the product
- **Replacing human incident commanders** — incidents that cannot be safely fixed are escalated, by design
- **Any additional action beyond sandboxed rollback** — expanding the allowlist dissolves the safety claim
- **Claiming production-grade accuracy** — results are 4/4 on four controlled scenarios and must be described that way
- **Random extra observability panels or unrelated features** — no feature is added unless an existing feature is removed first

## Context

**Hackathon frame.** Agents of SigNoz, run by WeMakeDevs with SigNoz. Track 01 is AI & Agent Observability. Judging explicitly rewards depth of SigNoz and OpenTelemetry integration — MCP server, Query Builder, dashboards, and alerts are called out by name. Repositories must contain `casting.yaml` and `casting.yaml.lock` so judges can re-run Foundry and reproduce the deployment. Use of AI assistants is permitted but must be declared; failure to disclose is disqualifying.

**Foundry.** SigNoz's deployment CLI (`foundryctl`). A single `casting.yaml` describes the whole deployment and Foundry generates the platform-specific manifests. Commands include `gauge` (validate tooling), `forge` (generate files), and `cast` (full deploy pipeline). It installs SigNoz and its MCP server in one step, and supports Docker Compose, systemd, and Render targets. Docker Compose is the target here.

**SigNoz MCP.** The MCP server exposes SigNoz observability data — metrics, traces, logs, alerts, dashboards, service performance — to LLM clients over the Model Context Protocol. SigNoz has published prior art on monitoring a LangChain agent that queries SigNoz MCP, which is closely adjacent to this project. Agent K's differentiator against that prior art is not "an agent that can query observability data" but the three enforcement layers wrapped around it.

**Why the failure modes are unusual.** AI applications degrade without throwing conventional server errors. They get slow, get expensive, answer wrong, or loop. Incident 2 exists specifically to prove this: user-facing error rates can stay flat while a cost SLO breach independently justifies a controlled rollback. This is the sharpest argument in the project and the demo should not bury it.

**Why the three laws are code, not prompt.** A prompt instruction to "always cite evidence" is a request. A renderer that deletes unsupported claims is a guarantee. The distinction is the entire pitch, and it is what separates this from a well-prompted assistant.

**Honesty posture.** Four scenarios, three runs each, is a small sample. The stated position is that this is acceptable for a hackathon provided the team never implies universal reliability, and that failed or confusing runs appear in the blog rather than being hidden.

## Constraints

- **Timeline**: Seven days, 2026-07-20 through 2026-07-26 — hackathon window, non-negotiable. Day-by-day plan is locked (see Roadmap).
- **Scope**: Locked by the founding spec. No feature is added unless an existing feature is removed first.
- **Tech stack**: FastAPI, PostgreSQL + pgvector, OpenTelemetry, SigNoz, Foundry, OpenRouter. One datastore, one LLM provider, one dashboard.
- **Agent architecture**: The Three Laws must be enforced in application code, never in prompt text. Any design that relies on model compliance for a safety property is invalid.
- **Action surface**: Exactly one allowlisted action — sandboxed rollback to the previous version. Two approvals and two denials must be demonstrable.
- **Budget**: Free-tier OpenRouter models for now; the specific model is expected to change. Nothing may depend on a particular model's identity.
- **Reproducibility**: `casting.yaml` and `casting.yaml.lock` committed; clean-machine rebuild must complete in under 15 minutes. This constrains dependency weight — no large local model downloads.
- **Reporting integrity**: Results reported as "4/4 on four controlled scenarios," never as general production accuracy. AI assistance disclosed in the submission.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent K is an explicit Python state machine, not an agent framework | The Three Laws are enforced by code and the investigation uses a fixed query set, so a framework's autonomy is the opposite of what is wanted. Owning every LLM call site is also what makes Law 3's exact token, cost, and duration accounting possible. | — Pending |
| Deterministic pipeline stages: collect → hypothesize → validate evidence → policy gate → act → verify → report | Makes each Law a discrete, testable gate rather than an emergent behavior. Each stage is independently instrumentable. | — Pending |
| OpenRouter as the single provider for chat *and* embeddings | Keeps "one LLM provider" literally true, one SDK, one base URL, one set of GenAI attributes. OpenRouter's `/api/v1/embeddings` endpoint removes the need for a local embedding model. | — Pending |
| No local embedding model (no torch / sentence-transformers) | A local model download would jeopardize the under-15-minute clean-machine rebuild target, which is a locked evaluation criterion. | — Pending |
| Default models pinned as config, not code: app `google/gemma-4-26b-a4b-it:free`, agent `openai/gpt-oss-20b:free`, embeddings `nvidia/llama-nemotron-embed-vl-1b-v2:free` | All free tier, all support the needed capabilities (function calling and structured output for the agent). The user expects to swap models later, so model identity must live in config. `cohere/north-mini-code:free` is the documented fallback if agent schema adherence proves flaky. | — Pending |
| Cost is computed from token counts against a configured price table, not read from provider billing | Free-tier models bill $0, which would make the cost SLO, the cost watchdog, and Incident 2 unfalsifiable. A configured price table makes cost meaningful, provider-independent, reproducible for judges without billing access, and stable across model swaps. Must be disclosed in the README as computed cost. | — Pending |
| Incident report renders to a Markdown file *and* to SigNoz spans | The file is diffable, survives the demo, and can be attached to the blog; the span copy keeps the audit trail inside SigNoz where the narrative wants it. Avoids building a report UI during an instrumentation-heavy week. | — Pending |
| Rollback executes via a separate deployer sidecar exposing only `POST /rollback` | Agent K never holds the Docker socket, so Law 2's "inside the permitted sandbox" check is enforced by process isolation rather than convention. This is the honest version of the safety claim and survives a judge probing it. | — Pending |
| Single Postgres instance serves both support data and vector retrieval | Keeps the architecture explainable and makes retrieval and database failures easy to observe — directly enabling Incidents 3 and 4. | — Pending |
| Track 01 (AI & Agent Observability) | Matches the project's thesis directly; judging criteria reward the SigNoz feature depth this project already requires. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-20 after initialization*
