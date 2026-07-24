# Prompt for Fable 5 — Kick off GSD: Discuss & Plan "Agent K"

Use your GSD workflow on this project. Run the **discuss phase first** — read everything below, then ask me about every ambiguity, gray area, or unstated decision you find. Do not assume anything or fill gaps yourself; confirm with me. Once the discussion is resolved, run the **plan phase** and produce the plan docs (phased implementation plan, file/module breakdown, day-by-day checklist) aligned to the locked 7-day build window below.

Everything after this point is context you must treat as fixed unless I say otherwise during discussion.

---

## 1. The Hackathon — "Agents of SigNoz" (WeMakeDevs × SigNoz)

**Link:** https://www.wemakedevs.org/hackathons/signoz

- **Dates:** July 20–26, 2026 (today is Day 1).
- **Prize pool:** $20,000 + job interviews at SigNoz for top submissions (interviews do not guarantee a job offer).
- **Tracks (pick one, or bring your own idea):**
  1. **Track 01 — AI & Agent Observability** (our track): trace, monitor, debug AI-native systems. Prize: one MacBook Air per team member (or cash equivalent).
  2. Track 02 — Signals & Dashboards: OpenTelemetry instrumentation & Query Builder mastery. Prize: iPad Air per member.
  3. Track 03 — Build Your Own: observe anything with SigNoz. Prize: iPhone Air per member.
- **Warm-up blog side-prize:** self-host SigNoz, write about a feature, submit before July 19 for AirPods Pro 3 / Beats Powerbeats Pro 2. *(Already done — submitted solo before the deadline.)*
- **Social Buzz side track:** top 10 social posts tagging @wemakedevs and @SigNozHQ get swag.

### Judging criteria (6, all matter)
1. **Potential Impact** — does it solve a meaningful problem / unlock a valuable use case?
2. **Creativity & Innovation** — how unique, does it push what's possible with observability?
3. **Technical Excellence** — implementation quality, clean/maintainable engineering.
4. **Best Use of SigNoz** — how deeply it leans on traces, metrics, logs, dashboards, alerts.
5. **User Experience** — intuitive, polished, something people would actually adopt.
6. **Presentation Quality** — demo, README, and submission clearly communicate problem/solution/impact.

### Agency Protocols (rules)
1. Solo or team of up to 4; team composition can change before the hackathon starts (it has now started, so ours is locked at 4).
2. Project **must use or integrate SigNoz** — the deeper the integration (MCP, traces, metrics, logs, dashboards, alerts), the stronger the score.
3. Any track, or a custom idea — example builds listed are inspiration only, not requirements.
4. Job interviews for top winners do not guarantee employment.
5. Third-party tools, frameworks, OSS libraries, public APIs, and CC-licensed assets are allowed; original work built on top of them is what's judged.
6. Submission form was "coming soon" as of the rules page — check the hackathon page again closer to the deadline for the actual submission requirements.
7. **AI assistant use (Claude Code, ChatGPT, Copilot, etc.) is permitted but must be disclosed in the submission.** Failure to disclose = disqualification.
8. Strategy/planning/discussion could happen before the hackathon start; **actual coding and design work only after the start** (i.e., from today, July 20, onward). Notes/sketches/diagrams beforehand were fine.
9. Teams are 1–4 members.
10. IP built during the hackathon belongs to the team; agree on ownership internally.
11. Standard code-of-conduct / no-harassment rule, enforced by immediate disqualification.

### SigNoz field requirements (mandatory, judged directly under criterion 4)
1. **Install SigNoz via Foundry** — Foundry installs SigNoz *and* its MCP server in one step. Quickstart: https://signoz.io/docs/install/docker/
2. Use as many SigNoz features as possible: **MCP server, Query Builder, dashboards, alerts** — this directly improves scoring.
3. **Repo must include `casting.yaml` and `casting.yaml.lock`** so judges can reproduce the deployment by re-running Foundry against them.

---

## 2. Our team constraints (locked — do not deviate)

- **Team of 4**, all majority web-tech background, **no prior Docker / DevOps / OpenTelemetry experience** on the team — plan onboarding/ramp-up accordingly, don't assume SigNoz/OTel fluency.
- **One team member is unavailable July 24–26** — account for this in task/day assignment.
- **Zero-budget constraint: only free tiers, open-source, or self-hosted tools.** The only paid tool in the loop is the Claude Code subscription used to *build* the project — nothing paid is allowed in the *shipped* product's runtime (no paid LLM APIs, no paid infra).
- **LLM provider decision (already locked):**
  - **Groq** as primary — `llama-3.1-8b-instant` for the RAG support app's high-volume answers, `llama-3.3-70b-versatile` for Agent K's own reasoning.
  - **Cerebras** as eval-day overflow capacity.
  - **Gemini Flash** (free tier) as a tool-calling fallback only.
  - All three sit behind a single OpenAI-compatible client module, provider selected via environment variable — optionally routed through **LiteLLM** (free, OSS, already documented in SigNoz's own observability docs).
  - **Embeddings:** local `sentence-transformers`, no external embedding API.
- Rule 8 window has closed — actual coding starts today, July 20.

---

## 3. The locked project idea: Agent K (Track 01)

> Reproduce this section exactly as our source-of-truth spec — this is the full, final project definition. Nothing here is a strawman; treat every stated behavior, law, incident, and target as a hard requirement unless discussion surfaces a real conflict.

### One-sentence definition

**Agent K is a code-enforced incident-response agent that investigates failures in an AI application using SigNoz, publishes only evidence-backed conclusions, takes action only when strict safety rules allow it, and records its own behavior so humans can audit everything it did.**

### The problem

AI applications can fail in unusual ways. They may become slow, expensive, inaccurate, or stuck in repeated loops without producing a normal server error.

An engineer usually has to search through traces, metrics, logs, alerts, and deployment history to understand what happened. This takes time, and an AI agent that investigates the incident can also make unsupported guesses or take unsafe actions.

**Agent K solves this by making every investigation traceable, every conclusion verifiable, and every action controlled by code.**

### What Agent K does

When an alert fires, Agent K:

1. Receives the alert from SigNoz.
2. Collects relevant traces, metrics, logs, and deployment information through the SigNoz MCP server.
3. Investigates the incident using a fixed set of queries.
4. Forms one or more possible root-cause explanations.
5. Attaches supporting SigNoz evidence to every explanation.
6. Decides whether a safe rollback is allowed.
7. Performs the rollback only if the code-based safety policy approves it.
8. Runs a verification query after the action.
9. Produces an auditable incident report.
10. Records its own cost, duration, queries, loops, decisions, and policy results in SigNoz.

Agent K is not simply a chatbot that answers questions. **It is an evidence-producing incident workflow with an AI investigator inside it.**

### The Three Laws (enforced by software, not prompts)

**Law 1 — No claim without evidence.** Agent K cannot publish a root-cause claim unless it has supporting evidence from SigNoz. Every claim carries: the claim text, a confidence value, the SigNoz query, the time range searched, and a resolvable evidence link (trace/log/metric/deployment). Example structure:

```json
{
  "claim": "The v2 prompt template caused the increase in failed responses.",
  "confidence": 0.94,
  "evidence": [
    {
      "type": "trace",
      "query": "Find failed requests after deployment v2",
      "time_range": "2026-07-20T10:00:00Z/2026-07-20T10:15:00Z",
      "link": "SigNoz deep link to the relevant traces"
    },
    {
      "type": "deployment",
      "query": "Find deployment marker for support-api v2",
      "time_range": "2026-07-20T09:55:00Z/2026-07-20T10:15:00Z",
      "link": "SigNoz deep link to the deployment event"
    }
  ]
}
```

The report renderer strips any claim with an empty evidence list — Agent K is technically unable to publish an unsupported assertion. Agent K also creates span links between investigation spans and the original incident traces, so a human can go from failure → agent reasoning in one click. A link checker (run during evaluation) confirms every generated evidence link resolves against the running SigNoz instance.

**Law 2 — No action without budget.** Agent K cannot execute an operational action just because the model recommends it. Before any action, a code-based policy checks:
1. Is the relevant SLO/burn-rate threshold actually breached?
2. Is the action on the approved allowlist?
3. Has the cooldown period passed?
4. Is confidence above the required threshold?
5. Does the evidence identify a deployment-related cause?
6. Is execution happening inside the permitted sandbox?

**The allowlist contains exactly one action: rollback to the previous application version.** Rollback process: confirm the incident ties to a recent deployment → confirm burn-rate/cost SLO breach → confirm rollback is allowed for this incident type → change the Docker Compose image/app tag to the previous version → create a deployment marker in SigNoz → wait for recovery → re-query SigNoz to verify → record the outcome.

If any safety check fails, Agent K does not act — it produces an evidence-linked recommendation for a human instead. Every policy decision becomes a telemetry span: requested action, incident ID, SLO value, threshold, confidence, allowlist result, cooldown result, final verdict, and reason.

**Law 3 — No self without telemetry.** Agent K observes itself as carefully as it observes the application: every LLM call, input/output token counts, estimated cost, investigation duration, number/type of MCP queries, query failures, repeated queries, number of hypotheses, confidence per hypothesis, policy decisions, actions attempted/approved/denied, verification results.

- **Loop breaker:** hashes each MCP query, stops the investigation if the same query repeats too many times → stops querying, records the loop event, fires a watchdog alert, marks the investigation incomplete, escalates to a human with evidence collected so far.
- **Cost watchdog:** if investigation exceeds the configured token/cost threshold, Agent K stops and reports it could not safely complete the investigation within budget.

### The application being monitored

**A FastAPI RAG support-answering service** — FastAPI API, PostgreSQL + pgvector (one datastore for both support data and vector retrieval, kept simple on purpose), one LLM provider, a retrieval step, a prompt-construction step, an answer-generation step, OpenTelemetry instrumentation, GenAI semantic-convention attributes on model calls, logs/metrics/traces → SigNoz. No Kubernetes, no worker/queue system, no unnecessary microservices — small enough to finish, reliable enough to demo.

### The four demonstration incidents (each deliberately seeded via a feature flag/config change — disclosed as controlled test failures)

**Incident 1 — Prompt-regression deployment.** Broken prompt template ships in a new version → failed-answer rate rises, error spans appear, problem starts right after deployment v2. Agent K: finds the error increase, connects it to the deployment marker, shows failed traces, decides rollback is safe, rolls back, verifies error rate normalizes. **Expected verdict: rollback allowed.**

**Incident 2 — Retry-storm cost runaway.** A config change lowers timeouts, causing repeated LLM calls. User-facing errors may stay low, but LLM calls/tokens/cost per minute spike and breach the cost SLO. Agent K: detects the cost breach, finds the repeated-call pattern, connects it to the new deployment, approves rollback because the cost SLO is breached, verifies call count/cost normalize. **Expected verdict: rollback allowed.** (Important differentiator: no HTTP errors needed — a cost SLO alone can justify a controlled rollback.)

**Incident 3 — Retrieval latency injection.** A feature flag adds artificial delay to the pgvector retrieval query → retrieval spans slow down, overall latency rises, trace waterfall clearly shows the DB retrieval as the bottleneck, no deployment-related cause. Agent K: identifies the retrieval query as the source, shows the trace waterfall, confirms rollback is NOT justified (not deployment-caused), recommends human investigation / removing the delay. **Expected verdict: rollback denied.**

**Incident 4 — Database pool exhaustion.** Too few DB connections configured → API errors rise, logs show connection-pool exhaustion, trace/log correlation identifies affected requests, rolling back the app version doesn't fix this class of failure. Agent K: finds the DB-pool errors in logs, links them to failed traces, explains rollback isn't supported for this failure type, recommends a human-approved restart/scaling/pool-config change. **Expected verdict: rollback denied.**

### The dashboard (one polished SigNoz dashboard, four sections)

1. **Service health** — request rate, error rate, request latency, retrieval latency, LLM latency, SLO status, burn rate, current deployment version.
2. **Incident context** — active alerts, deployment markers, incident start time, affected service, related trace IDs, current suspected cause, links to relevant traces/logs/metrics.
3. **Agent health** — cost per investigation, token usage, investigation duration, MCP query count, query failures, repeated-query count, hypothesis confidence, investigation success rate, watchdog alerts.
4. **Action audit trail** — proposed action, policy checks, SLO value, confidence value, allow/deny verdict, action execution time, verification result, human escalation status.

Alerts are configured separately from the dashboard so alerting can be demoed without cluttering it.

### SigNoz features that must be visibly used

OpenTelemetry traces, OpenTelemetry metrics, structured logs, GenAI semantic-convention attributes, SigNoz dashboards, SigNoz alerts, Query Builder, SigNoz MCP, trace-to-log correlation, trace links and span links, deployment markers, Foundry deployment, `casting.yaml`, `casting.yaml.lock`. Goal: SigNoz is the central operating system for the whole investigation, not a single trace mentioned in the README.

### Evaluation targets (locked, report honestly — 3 runs per incident)

- 4/4 top-level diagnoses correct on the four seeded scenarios — described honestly as "4 out of 4 on four controlled scenarios," never as general production accuracy.
- 100% of rendered evidence links resolve against the local SigNoz instance.
- Zero actions execute outside the policy gate.
- Exactly **two rollback approvals and two rollback denials** recorded.
- Median investigation cost stays below the configured watchdog threshold.
- Loop breaker demonstrably stops repeated MCP queries.
- Every investigation span contains valid self-telemetry.
- Clean-machine Foundry rebuild completes in under 15 minutes.
- The two rollback scenarios are compared against a scripted manual baseline.
- Time-to-correct-diagnosis is reported for every run.
- Any failed run or confusing result gets reported in the blog, not hidden.

### Seven-day build plan (locked — plan phase must map onto this)

- **Jul 20 (Day 1):** Install SigNoz via Foundry; commit `casting.yaml` + `casting.yaml.lock`; scaffold FastAPI app; add PostgreSQL + pgvector; add OpenTelemetry; confirm traces/metrics/logs reach SigNoz.
- **Jul 21 (Day 2):** Add service SLOs; add burn-rate alerts; add deployment markers; implement the four failure flags; test every failure manually; confirm each produces distinguishable telemetry.
- **Jul 22 (Day 3):** Build the Agent K workflow; connect the alert trigger; connect the SigNoz MCP server; add investigation queries; create the structured RCA schema; record every query as evidence.
- **Jul 23 (Day 4):** Implement Law 1; build the evidence validator; strip unsupported claims from reports; generate SigNoz deep links; add the automated link checker; add span links between investigations and incident traces.
- **Jul 24 (Day 5):** Implement Law 2; build the policy module; add the rollback allowlist; add cooldown/confidence checks; add the rollback executor; add post-rollback verification; record every policy verdict as telemetry. *(Team member is unavailable from today through Day 7 — plan around this.)*
- **Jul 25 (Day 6):** Implement Law 3; add agent token/cost metrics; add duration histograms; add query-loop detection; add cost watchdog alerts; finish the dashboard and action audit trail.
- **Jul 26 (Day 7):** Run every incident 3x; record diagnosis accuracy; measure investigation cost; measure time-to-diagnosis; measure rollback results; compare against manual baseline; test clean-machine rebuild; freeze code; capture screenshots/demo footage; write the submission blog from the actual build log.

### Demo script (15 beats)

1. Show the monitored AI support service working normally.
2. Trigger the prompt-regression failure.
3. Show the SigNoz alert.
4. Let Agent K investigate through MCP.
5. Open the structured report.
6. Click from the claim to the supporting trace and deployment marker.
7. Show the policy checks.
8. Show the approved rollback.
9. Show the verification query proving recovery.
10. Trigger the retrieval-latency failure.
11. Show the trace waterfall identifying the database delay.
12. Show the denied rollback and evidence-linked escalation.
13. Show Agent K's own cost and query telemetry.
14. Trigger or simulate a repeated-query loop.
15. Show the watchdog stopping the investigation.

Closing message: *"Agent K does not ask you to trust an AI agent with production. It makes the agent prove what it knows, earn the right to act, and leave receipts for every decision."*

### What Agent K is explicitly NOT

A general-purpose chatbot; a dashboard with a chat box; an unsupervised production remediation bot; a generic LLM cost tracker; a replacement for human incident commanders; a claim that four test cases prove production readiness; a collection of random observability panels; a project with five unrelated features.

### Locked scope (final — no additions unless an existing feature is removed first)

Track 01: AI and Agent Observability · one FastAPI RAG support application · one PostgreSQL+pgvector datastore · one LLM provider · four seeded incidents · one allowed action (sandboxed rollback) · two allowed verdicts and two denied verdicts · one SigNoz dashboard · separate alerts · Three Laws enforced in code · evidence-linked claims only · MCP used for investigation · agent self-telemetry required · Foundry deployment required · seven-day implementation window · AI assistance disclosed · results reported honestly.

---

## 4. Visual reference (infographic, for dashboard/UI design — not a spec)

We also have a one-page infographic summarizing Agent K visually, laid out in four quadrants around a "how it works" strip:

- **Top strip — 10-step pipeline icons:** Alert Received → Collect Evidence → Investigate → Find Possible Root Causes → Attach Evidence → Check Safety Policy → Take Action (If Allowed) → Verify Result → Create Incident Report → Observe Itself, captioned "Agent K is an evidence-producing incident workflow with a safe action engine and self-observability," with an MCP Server ↔ SigNoz connector noting "all data, evidence, actions and telemetry are stored in SigNoz."
- **Bottom-left — The Three Laws as three color-coded cards** (blue/green/purple), each with its bullet checklist plus a small example box (Law 1: an example evidence-backed claim card; Law 2: a green "if all checks pass → rollback" box next to a red "if any check fails → no action, escalate" box; Law 3: bullet list plus a "why this matters — humans can audit everything" note).
- **Bottom-middle — End-to-end example walkthrough** (7 steps: Alert → Investigate → Root Cause → Policy Check → Action → Verify → Report), each paired with a small "what Agent K saw in SigNoz" visual: an error-rate spike chart, a trace waterfall, a deployment-marker timeline dot, a burn-rate/confidence readout with an "ALLOW" badge, a Docker image-tag switch, a recovery line chart, and a report icon — ending in a green "Incident Resolved Automatically" outcome box, with a branch showing "if action not allowed → Agent K creates a recommendation and escalates to humans."
- **Bottom-right — Self-Observability Dashboard mockup** with illustrative sample metrics (not literal targets — the real evaluation targets are in section 3 above): KPI tiles for total incidents handled, total cost, average duration, actions taken; sparkline charts for LLM tokens used, queries executed, and reasoning loops; a policy-decisions donut chart (allowed/denied/escalated split); and a "recent decisions" table with timestamp, decision text, confidence, and a verdict badge (Allowed/Denied/Escalated).
- **Footer bar — four value props:** Evidence-First ("no claim without proof"), Safety-First ("only safe actions, only when allowed"), Transparent ("everything is recorded and auditable"), Faster MTTR ("resolve incidents in minutes, not hours").

Use this only to inform the visual design of the real SigNoz dashboard and the incident-report UI — the numbers shown are mock/sample data, not commitments.

---

## 5. What I need from you now

1. **Discuss phase:** Go through sections 1–4 and list every ambiguity, gray area, or missing decision you find (schema details, exact incident-seeding mechanism, rollback executor implementation, dashboard build tooling, alert config specifics, anything else). Ask me directly — don't assume or fill gaps yourself.
2. **Plan phase:** Once resolved, produce the plan docs — a phased implementation plan with concrete engineering tasks, file/module structure, and a day-by-day checklist mapped onto the locked 7-day build plan in section 3, honoring the zero-budget and team constraints in section 2.