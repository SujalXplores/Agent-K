# Feature Research

**Domain:** AI-powered incident-response / root-cause-analysis (RCA) agent — evidence-gated, safety-gated, self-observed. Built on SigNoz for the Agents of SigNoz hackathon, Track 01 (AI & Agent Observability).
**Researched:** 2026-07-20
**Confidence:** MEDIUM-HIGH — SigNoz-specific claims are HIGH confidence (official docs/blogs, cross-checked). Commercial AI-SRE competitor claims are MEDIUM confidence (vendor marketing/blog sources, cross-checked across 2-3 independent write-ups each, not independently benchmarked).

**Scope note:** Agent K's feature set is locked in `.planning/PROJECT.md`. This document does not propose additions. It classifies the locked feature set against what the AI-incident-response product class normally does, so the roadmap can tell which locked items are baseline expectations versus genuine points of differentiation, and which SigNoz capabilities are exercised, ambiguous, or left untouched.

---

## Feature Landscape

### Table Stakes (Expected of This Product Class)

Every credible AI-SRE / incident-copilot product surveyed (Cleric, Traversal, Resolve.ai, Rootly AI SRE, incident.io AI SRE / Investigations, Datadog Bits AI, PagerDuty SRE Agent, k8sgpt) does these things. Missing any of them would make Agent K look like a toy relative to the category it's entering.

| Feature | Why Expected | Complexity | Locked-scope status |
|---------|--------------|------------|----------|
| Multi-signal telemetry ingestion (traces + metrics + logs) | Universal baseline for any RCA tool; without all three signal types the tool can only see part of the failure | LOW (OTel SDK auto/manual instrumentation) | Covered — "OpenTelemetry traces, metrics, and structured logs shipped to SigNoz" |
| Automatic cross-signal correlation during investigation (trace↔log↔metric) | SigNoz's own MCP investigation post treats this as the core value prop of the MCP server; every competitor markets "one thread, one root cause" as the alternative to manual dashboard-hopping | MEDIUM (requires trace_id/span_id propagation into logs, consistent service/resource attributes) | Covered — trace-to-log correlation implied by "collect" stage of the pipeline and SigNoz's native OTel correlation |
| Change/deployment awareness as an RCA input | Checking "what deployed recently" is the single most common first move in both human and AI-driven RCA (Datadog Bits AI, PagerDuty SRE Agent, and generic SRE practice all treat deploys as the top hypothesis source) | LOW-MEDIUM | Covered — "deployment-related cause" is one of the six policy-gate checks; Incident 1 is a prompt regression tied to a version change |
| Ranked hypothesis with visible reasoning, not just a verdict | Rootly AI SRE, Traversal, and Cleric all surface a reasoning chain or ranked candidate causes with confidence, explicitly because a bare verdict without visible reasoning is why engineers don't trust AI SRE output | LOW-MEDIUM (mostly a rendering/schema concern once evidence exists) | Covered — claim schema includes confidence, evidence[], and relationship fields |
| Human-readable incident report artifact | Every surveyed tool ends an investigation with a document (postmortem draft, Slack thread summary, ticket) a human can read without touching the tool itself | LOW | Covered — Markdown report + SigNoz spans |
| Recommendation-only fallback when confidence or preconditions aren't met | Universal industry position (found across Rootly, Cleric, incident.io, InfoWorld/CNCF commentary): "human approval is still essential for... production remediation, rollback decisions, and final root cause conclusions" | LOW-MEDIUM | Covered — "Evidence-linked human recommendation produced whenever a check fails" |
| Cost/token instrumentation of the *monitored application's* LLM calls | Now standard practice for any GenAI app observability story since OTel's GenAI semantic conventions (`gen_ai.usage.input_tokens`, `gen_ai.request.model`, etc.) reached wide tool adoption in 2025-2026 | LOW-MEDIUM | Covered — "GenAI semantic-convention attributes on all model calls" |
| Some form of "read-only investigation is always safe, action is not" boundary | Every credible vendor gates remediation behind approval; Cleric explicitly limits itself to observation-only | LOW (as a design stance) / MEDIUM (to enforce it structurally) | Covered — policy gate before any action, single-entry allowlist |

**Framing for the roadmap:** the table-stakes list above is large — Agent K's locked scope already clears essentially all of it. That means judges and reviewers familiar with the category will not see the base loop (ingest → correlate → hypothesize → report) as novel. The differentiators below are where the actual pitch has to land.

### Differentiators (What Sets Agent K Apart)

These are the things surveyed competitors and SigNoz's own published prior art do **not** demonstrate together. Value proposition is stated relative to both the commercial AI-SRE field and SigNoz's own blog posts (see Prior Art Gap Analysis below).

| Feature | Value Proposition | Complexity | Locked-scope status |
|---------|-------------------|------------|----------|
| Code-enforced evidence validator (deletes unsupported claims before render) | Commercial tools show confidence scores and "reasoning chains" as a UI convenience — a *display* of trustworthiness, not a structural guarantee. Research on claim-evidence grounding (citation-grounded LLM pattern: "refuses to answer when the link cannot be made") describes exactly this pattern in the literature, but none of the surveyed commercial AI-SRE products document doing it in code. This is Agent K's single sharpest claim. | MEDIUM | Covered — "Evidence validator that strips any claim with an empty evidence list before rendering" |
| Automated link-checker verifying every rendered evidence link resolves against the *live* running SigNoz instance | Citation research distinguishes three rubrics: structural, resolvability, semantic. Most cited systems check resolvability abstractly (does a URL/ID exist in a corpus); verifying against a live, running observability backend as part of the submission's reproducibility story is unusual and directly answers "prove your links aren't decorative." | LOW-MEDIUM (once deep-link generation exists, this is a scripted HTTP check) | Covered |
| Span links connecting investigation spans to the original incident's trace | SigNoz documents span links as a general causal-relationship primitive (its public examples are async/background-job correlation). Using them specifically for agent-investigation provenance — "this diagnosis span is causally linked to the incident span it diagnosed" — is a deliberate, less commonly demonstrated usage and is a concrete, visible SigNoz feature depth signal for judges. | MEDIUM-HIGH (requires the agent to capture and propagate the original incident trace/span ID through the whole investigation pipeline) | Covered |
| Multi-check code-based policy gate (SLO breach, allowlist, cooldown, confidence, deployment-relatedness, sandbox) with every verdict emitted as its own telemetry span, decision inputs and all | Industry consensus is "gate remediation behind human approval" — but that's described as a *process* (a Slack approval bot, a PR review), not as a codified, inspectable set of independent checks each surfaced as its own auditable telemetry artifact. No surveyed source — commercial or SigNoz's own posts — shows this. | MEDIUM-HIGH | Covered |
| An actual action taken (sandboxed rollback) with post-action verification query, evaluated as 2 approvals / 2 denials | Most read-only tools (Cleric, incident.io Investigations) stop at recommendation. The aggressive-automation outlier (Resolve.ai, targeting ~80% auto-resolution) does not publish a small, falsifiable approve/deny evaluation design. A single tightly-scoped action with a designed 2-and-2 test is a different, more auditable kind of claim than either extreme. | MEDIUM-HIGH | Covered |
| Full self-observability of the investigator agent itself: computed cost, query-hash loop detection, budget watchdog halting an in-flight investigation | SigNoz's own LangChain-MCP blog *already shows partial agent self-observability* (dashboard panels for p95 latency, tool-call distribution, token usage, error rate) — see gap analysis. It does not show computed dollar cost, loop detection, or a budget-triggered halt. This is the most direct "goes beyond SigNoz's own published prior art" claim available. | MEDIUM | Covered — Law 3 |
| Cost-only failure mode (Incident 2: flat error rate, cost SLO breach) | Nearly all public RCA demos (commercial and SigNoz's own) key off error-rate or latency spikes. A scenario where user-facing errors stay flat while an independent signal (cost) justifies a rollback is a distinct claim about *why AI-application failure modes need different instrumentation than conventional services* — not commonly staged in the surveyed material. | LOW (as a demo design choice, given the telemetry already exists) | Covered — explicitly called out in PROJECT.md as "the sharpest argument in the project" |
| One-command reproducible deployment (Foundry `casting.yaml`/`casting.yaml.lock`) making the whole evidence trail + policy gate + self-telemetry independently re-runnable | Most AI-SRE demos are screenshots or video only; reproducibility as a submission-level differentiator is uncommon and directly serves the hackathon's own judging criteria (re-runnable via Foundry). | MEDIUM (mostly a packaging/ops concern, not a new capability) | Covered |

### Anti-Features (Deliberately Not Built)

Cross-checked against `.planning/PROJECT.md`'s Out of Scope list. Each row also notes what the surveyed competitive field does instead, so the roadmap understands these are *informed* exclusions, not oversights.

| Anti-Feature | Why It Looks Appealing | Why Agent K Excludes It | What the Field Does Instead |
|--------------|------------------------|--------------------------|------------------------------|
| Kubernetes / worker queues / extra microservices | Broader infra surface = looks more "production-grade"; k8sgpt and several AIOps tools specialize entirely in K8s | Breaks the 7-day, live-demo-reliable constraint; adds a whole failure-mode class unrelated to the Three Laws thesis | k8sgpt and similar tools trade generality for depth in exactly one infra layer — Agent K makes the equivalent trade toward one application and one action instead |
| General chatbot / dashboard-with-chat-box | Chat is the default UX for "AI + observability" (Datadog Bits AI and incident.io both surface as Slack-thread conversational tools) | Conflicts with the stated thesis: Agent K is a workflow with enforced gates, not a conversational surface whose safety depends on what gets typed into it | Commercial tools use chat because it fits existing on-call workflow; Agent K trades that familiarity for a demonstrably code-enforced pipeline |
| Unsupervised production remediation / expanding the action allowlist beyond rollback | Resolve.ai markets ~80% auto-resolution as a headline number; broader remediation breadth reads as more capable | Every additional allowlisted action multiplies the paths that must be proven safe within a week; the differentiator is depth of guarantee on one action, not breadth of actions | Aggressive-automation vendors accept this risk at enterprise scale with dedicated safety teams; not a fair comparison for a hackathon-week build |
| Generic LLM cost tracker as the product itself | Cost/FinOps-for-LLM is a standalone product category some teams would find valuable on its own | Cost telemetry exists only to feed the policy gate (Law 2's SLO-breach check and Law 3's budget watchdog) — making it the product would dilute the Three Laws thesis | Dedicated LLM cost tools expose cost as the primary UI; Agent K treats it as an internal control signal |
| Replacing human incident commanders | Full autonomy is the implicit "end state" narrative some AI-SRE marketing gestures toward | Directly conflicts with universal industry consensus found in research: "human approval is still essential for... rollback decisions, and final root cause conclusions" (cross-vendor). Escalation-on-failure is by design. | Every credible vendor surveyed (IBM Instana, incident.io, Rootly, Cleric) already positions itself as augmenting, not replacing, on-call humans — this exclusion is now baseline good practice industry-wide, not even a differentiator |
| Claiming production-grade accuracy from a small sample | Competitors publish aggregate accuracy numbers (Traversal: 82% RCA accuracy across 250B log lines/day at American Express; incident.io: 90% accuracy in autonomous investigation) which creates pressure to publish a comparable-sounding number | Those percentages come from large real-world fleets over long periods; a 4-scenario, 3-run hackathon sample cannot support the same statistical claim, and asserting it would be the exact hallucination-and-overclaim failure mode this project exists to avoid | Report "4/4 on four controlled scenarios," never as a percentage implying broader generalization |
| Extra dashboard panels/features unrelated to the Three Laws | Judging rewards SigNoz feature depth, creating temptation to add panels just to demonstrate more SigNoz surface | Explicit rule: no feature added unless an existing one is removed first; panels not wired to evidence, policy, or self-observability wouldn't demonstrate depth, just clutter | See SigNoz Feature Inventory below for feature depth that comes from the *existing* four-section dashboard requirement, not additional panels |

---

## Prior Art Gap Analysis: SigNoz's Own Published Material

This is the most important section for judging risk: a Track 01 submission that merely reproduces an existing SigNoz blog post is structurally weak. Three SigNoz posts are directly adjacent to Agent K and were read in full for this research.

### 1. "Monitoring a LangChain Agent Querying the SigNoz MCP Server" (signoz.io/blog/monitoring-langchain-agent-querying-signoz-mcp-server)

**What it shows:** A LangGraph agent answers natural-language operational questions ("what are all the active services in the last 5 hours," "which service has the highest error rate this week") by calling the SigNoz MCP server for logs/metrics/traces, then synthesizes a plain-language answer. The agent itself is instrumented with OpenTelemetry, and a SigNoz dashboard tracks the agent's own p95 latency, tool-call distribution, token usage, and error rate.

**What it does NOT show:** RCA hypothesis generation, evidence citation with a validated schema, safety/policy gating of any kind, any action taken beyond answering a query, alerts, or the Query Builder explicitly.

**Gap for Agent K:** This post is the closest published prior art and the one most likely to be cited by judges as "hasn't SigNoz already done this?" The honest answer: it demonstrates the *read path* (agent queries MCP, agent is observable) that Agent K's "collect" stage also uses, and it demonstrates partial self-observability (latency/tokens/errors on a dashboard). It demonstrates **none** of Law 1 (evidence validation, link-checking, span links), **none** of Law 2 (policy gate, action, rollback), and only a subset of Law 3 (no computed cost, no loop detection, no budget watchdog — those require deliberately induced repetition/runaway scenarios this post never stages). A submission that stopped at "agent queries MCP and answers questions" would be a near-duplicate of this post; Agent K's locked scope is already well past that line.

### 2. "SigNoz MCP: Log and Trace Investigation" (signoz.io/blog/signoz-mcp-log-trace-investigation)

**What it shows:** A human investigator uses the MCP server conversationally to go from a vague symptom to a specific failing span (a `PaymentService/Charge` failure affecting gold-tier users) via natural-language log queries, trace analysis, and automatic log↔trace correlation — without knowing service names or field names in advance.

**What it does NOT show:** Any autonomous agent — this is human-in-the-loop investigation, not agent-driven RCA. No evidence schema, no safety gating, no action, no self-observability. Also explicitly does not cover Query Builder, dashboard creation, alert configuration, or metrics querying.

**Gap for Agent K:** This post establishes that SigNoz's MCP server is capable of exactly the kind of query-by-symptom investigation Agent K's "collect" and "hypothesize" stages need — it's validation that the data path is sound, not competition for the product. Agent K's novelty relative to this post is that the investigator is an autonomous agent operating under Laws 1-3, not a human typing prompts.

### 3. "Introducing Agent-Native Observability" (signoz.io/blog/introducing-agent-native-observability)

**What it shows:** SigNoz's positioning/vision piece for agent-native observability. States a philosophy that maps almost exactly onto Agent K's Law 2: *"Agents should gather evidence, correlate telemetry, and propose causes. Humans should set alert policy, choose what deserves a page."* Lists a live MCP server (SigNoz Cloud + open-source self-hosted) as the current concrete feature, and a roadmap of near-term items including an in-UI AI Assistant, instrumentation "skills," schema-drift detection, and — notably — **"Investigation-to-Policy workflows"** (converting debugging sessions into automated alerts) as a *future*, not-yet-shipped item.

**What it does NOT show:** Any working implementation of policy gating, evidence-linked claims, an enforced action, or agent self-observability (cost, loop detection). It is a strategy/vision post, not a demo.

**Gap for Agent K:** This is the strongest validation of the project's thesis and simultaneously the strongest evidence of novelty. SigNoz has publicly stated the philosophy Agent K encodes in Law 2 ("agents propose, humans decide") but has not shipped or demonstrated a working version of it — "investigation-to-policy workflows" is explicitly named as forthcoming, not present. Agent K's policy module is a working, code-enforced, telemetry-visible instance of exactly what this post gestures at as future work. This is the single most defensible "novel, not a reproduction" claim available and should be foregrounded in the submission narrative.

### Summary judgment

A weak Track 01 submission in this exact niche would: connect an agent to SigNoz MCP, let it answer questions in natural language, and put a dashboard on top showing the agent's own latency/token/error stats. That submission would substantially duplicate post #1. Agent K's locked scope already requires evidence validation with a code-enforced deletion rule, a link-checker against the live instance, span links for provenance, a six-check policy gate with per-verdict telemetry, an actual gated action with an explicit approve/deny test design, and loop/cost/budget self-observability beyond what post #1's dashboard shows. None of that is additive scope creep to propose — it is already locked, and this gap analysis is the evidence that it's the right locked scope relative to what SigNoz itself has already shown.

---

## SigNoz Feature Inventory

Enumerates SigNoz-native capabilities a submission could visibly exercise, with effort to exercise *meaningfully* (not just "install it") and where the locked scope stands. Judging explicitly names MCP server, Query Builder, dashboards, and alerts as rewarded depth signals.

| SigNoz Feature | What It Does | Effort to Exercise Meaningfully | Locked-Scope Status |
|----------------|---------------|----------------------------------|----------------------|
| OTel traces | Distributed tracing across the FastAPI app, agent, and deployer sidecar | LOW — standard OTel SDK instrumentation | Covered |
| OTel metrics | Service health, cost, and investigation-level metrics | LOW-MEDIUM — needs custom metrics beyond auto-instrumentation (cost, MCP query counts, hypothesis confidence) | Covered |
| Structured logs (OTel) | RAG service and agent logging, correlated to traces | LOW-MEDIUM — requires consistent trace_id/span_id propagation into log records | Covered |
| Trace-to-log correlation | Jump from a span to the logs fired during it and back; SigNoz does this natively via trace_id/span_id fields | MEDIUM — automatic once fields are populated correctly, but requires the app not to break the propagation (e.g., across async boundaries, the deployer sidecar) | Covered implicitly — required for evidence gathering during "collect"/"validate evidence" stages |
| Span links | Causal reference between spans not in direct parent-child relation | MEDIUM-HIGH — must be explicitly created in code linking investigation spans to the original incident trace; SigNoz's own public examples of this feature are async/background-job correlation, not agent-audit provenance, so this is a less-trodden usage | Covered — explicit locked requirement, and a differentiator (see above) |
| Query Builder | Visual filtering/aggregation across logs, traces, metrics without raw ClickHouse/PromQL | LOW — used indirectly any time MCP or the dashboard issues a query; direct exercise (e.g., building a dashboard panel manually) is trivial once telemetry exists | Covered — underlies every dashboard panel and every evidence query |
| Dashboards | Custom panel layouts | LOW-MEDIUM for a basic dashboard; MEDIUM for a well-organized four-section one that tells a coherent story to a judge scanning quickly | Covered — one dashboard, four sections (service health, incident context, agent health, action audit trail) is the locked requirement |
| Alerts | Rule-based notification on metric/log/trace conditions | LOW-MEDIUM — straightforward once the underlying metrics exist; the design decision to configure them *separately* from the dashboard (rather than reusing dashboard panels) is a locked choice that visibly exercises the alerts feature as its own artifact, not folded into panels | Covered |
| SLOs / burn-rate alerting (SigNoz-native SLO objects) | Error-budget-based alerting: alert on rate of budget consumption rather than absolute threshold | MEDIUM-HIGH if implemented as a first-class SigNoz SLO object with burn-rate math; LOW if "SLO breach" is instead a manually computed condition inside the policy module reading raw metrics | **Ambiguous in locked scope** — PROJECT.md names "SLO breach" as a Law 2 policy-gate input and frames Incident 2 around a "cost SLO breach," but does not specify whether this uses SigNoz's native SLO/burn-rate alerting feature or an internally computed check against metrics queried via MCP/Query Builder. This is a requirements-definition question, not a scope-addition — worth resolving explicitly, since a native SigNoz SLO object is a more visible feature-depth signal to judges than an equivalent internal calculation, at comparable implementation cost. |
| MCP server | Exposes traces/metrics/logs/alerts/dashboards to LLM clients over MCP; installed by Foundry in one step | LOW to have available; MEDIUM-HIGH to exercise *meaningfully* — requires designing a specific, bounded query strategy the agent follows per incident type, not open-ended tool use | Covered — "SigNoz MCP server as the investigation data path" is the core data path for the whole project |
| Deployment markers / before-after-deploy comparison (Query Builder time-shift) | Compare metrics before/after a deploy event; used to visually confirm a deployment-caused regression | LOW-MEDIUM once a deploy event exists to mark | **Not explicitly named in locked scope.** The "deployment-related cause" policy check and Incident 1 (prompt regression tied to a version) imply deployment awareness exists somewhere in the pipeline, but PROJECT.md doesn't name SigNoz's deployment-marker/time-shift comparison feature specifically as the mechanism. Worth flagging for requirements-definition as a feature that's implicitly relevant but not confirmed as visibly exercised. |
| GenAI semantic-convention attributes | Standard `gen_ai.*` span/metric attributes for LLM calls (`gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `gen_ai.client.token.usage`, `gen_ai.client.operation.duration`) | LOW-MEDIUM — mechanical to add once the LLM call sites are centralized (which the "explicit Python state machine, not a framework" architecture decision already supports) | Covered — explicit locked requirement, and directly reused for computed cost in Law 3 |
| Dashboards-as-code / Alerts-as-code (Terraform provider `SigNoz/signoz`) | Manage dashboards and alert rules as version-controlled Terraform resources instead of UI clicks | MEDIUM — separate tool (Terraform) and provider setup, plus state management, on top of an already tight 7-day build | **Not in locked scope.** PROJECT.md requires "one SigNoz dashboard" and "SigNoz alerts configured separately from the dashboard" but does not specify Terraform/IaC provisioning. This is a SigNoz feature judging could reward that the locked scope visibly omits — noted for the record, not proposed as an addition. |

**Net assessment:** the locked scope exercises MCP server, traces, metrics, logs, trace-log correlation, span links, Query Builder (indirectly), dashboards, alerts, and GenAI semantic conventions — covering essentially every SigNoz feature judging explicitly names except dashboards/alerts-as-code, which is omitted, and native SLO/burn-rate objects, whose implementation path is ambiguous in the current spec. Both are flagged for the requirements-definition phase to resolve or consciously accept as omitted, not as scope to add.

---

## Feature Dependencies

```
OTel traces/metrics/logs shipped to SigNoz
    └──requires──> GenAI semantic-convention attributes on model calls (Law 3 cost/token base)
    └──requires──> SigNoz deep-link generation (Law 1)
                       └──requires──> Structured RCA claim schema
                                          └──requires──> Evidence validator (strips unsupported claims)
                                                             └──requires──> Automated link checker (verifies links resolve)
    └──requires──> Span links connecting investigation spans to incident traces (Law 1)

Per-LLM-call instrumentation (tokens, cost, duration)
    └──requires──> GenAI semantic-convention attributes
    └──enables──>  Investigation-level metrics (duration, MCP query count, failures, repeats, confidence)
                       └──enables──> Loop breaker (hashes MCP queries, halts on repetition)
                       └──enables──> Cost watchdog (halts on budget exceeded)

Structured RCA claim schema + Evidence validator
    └──enables──>  Code-based policy module (six checks: SLO breach, allowlist, cooldown,
                    confidence, deployment-relatedness, sandbox)
                       └──requires──> SLO-breach signal (metrics query — native SigNoz SLO or
                                       internally computed, see ambiguity flagged above)
                       └──requires──> Confidence field from claim schema
                       └──requires──> Deployment-relatedness field from claim schema
                       └──enables──>  Rollback executor (only on all-checks-pass)
                                          └──requires──> Deployer sidecar (POST /rollback,
                                                          process-isolated from Agent K)
                                          └──enables──>  Post-action verification query
                       └──enables──>  Evidence-linked human recommendation (on any check failure)

Policy verdicts + action audit
    └──requires──> Every policy verdict emitted as its own telemetry span (full inputs + reason)

One SigNoz dashboard (four sections)
    └──requires──> Traces + metrics + logs (service health section)
    └──requires──> Evidence-validated claims + span links (incident context section)
    └──requires──> Law 3 self-observability metrics (agent health section)
    └──requires──> Policy verdict spans + rollback executor output (action audit trail section)

SigNoz alerts (configured separately from dashboard)
    └──requires──> Metrics/SLO signals already flowing (same base as dashboard's service-health section)

Four seeded incidents + evaluation
    └──requires──> The entire pipeline above functioning end-to-end
    └──requires──> Flag-controlled fault injection in the FastAPI/Postgres app
    └──requires──> Scripted manual baseline (independent of the agent, for comparison)

Foundry deployment (casting.yaml/.lock)
    └──requires──> All SigNoz-side configuration (dashboard, alerts, MCP) expressible/reproducible
                    within a clean-machine rebuild under 15 minutes
```

### Dependency Notes

- **Evidence validator requires the claim schema to exist first** — the schema (claim, confidence, evidence[], query, time range, link, relationship) is the contract the validator enforces; building the validator before the schema is stable would mean redoing it.
- **Policy gate requires both Law 1 outputs (confidence, deployment-relatedness) and Law 3 outputs (cost/budget state, SLO signal)** — it is the point where investigation results and self-observability converge, so it cannot be built or meaningfully tested until both are producing real values, not stubs.
- **Rollback executor requires the deployer sidecar to exist and be network-reachable but privilege-isolated** — this is a hard sequencing point: the sidecar (a separate process holding the Docker socket) has to be stood up before the executor can be tested end-to-end, and the isolation property (Agent K never holds the Docker socket) is precisely what makes Law 2's "inside the sandbox" check meaningful rather than cosmetic.
- **Dashboard's four sections each pull from a different upstream feature** — this means the dashboard is necessarily one of the last things wired up correctly, even though panel *scaffolding* can start early; a dashboard built before the underlying telemetry is stable will need rework.
- **Native SLO objects vs. internally computed SLO checks are not interchangeable for the policy gate** — if the roadmap resolves the ambiguity flagged in the SigNoz Feature Inventory toward native SigNoz SLOs, that determination should happen before the policy module's SLO-breach check is implemented, since the two approaches have different query surfaces (a SigNoz SLO API/query vs. a raw metrics Query Builder call).

---

## MVP Definition

Scope is locked; there is no "add after validation" tier within the hackathon window. This section maps the standard MVP-tiering exercise onto the locked scope so the roadmap can see what's core-path (must work for the thesis to hold) versus supporting (must exist, but a rough edge here is more survivable).

### Launch With (v1) — the entire locked Active scope

Everything in PROJECT.md's Active requirements is v1; none of it is deferrable within the seven days. Within that, the following are the load-bearing items — if any one of these is missing or broken, the project's stated thesis fails, independent of polish elsewhere:

- [ ] Evidence validator that strips unsupported claims — this is Law 1's entire enforcement mechanism
- [ ] Code-based policy module with all six checks, each emitted as a telemetry span — this is Law 2's entire enforcement mechanism
- [ ] Loop breaker and cost watchdog actually halting an investigation, not just logging — this is Law 3's entire enforcement mechanism (self-observability that never triggers a halt is just a dashboard, not a law)
- [ ] Two demonstrable rollback approvals and two demonstrable denials — this is the evaluation design that proves the policy gate discriminates rather than always saying yes or always saying no
- [ ] Automated link checker against the live SigNoz instance — this is what makes "evidence-first" a checkable claim rather than an assertion

### Explicitly Deferred (per PROJECT.md's Out of Scope — not new proposals)

These are named in PROJECT.md as intentionally out of scope for this milestone; restated here only to make the MVP boundary explicit for the roadmap, not as recommendations to add later:

- Expanding the action allowlist beyond rollback
- Unsupervised/production-scope remediation
- Kubernetes or multi-service architecture
- A conversational/chat interface layered on top of the workflow
- Dashboards-as-code / alerts-as-code via Terraform (see SigNoz Feature Inventory — omitted, not deferred with intent to add)

---

## Feature Prioritization Matrix

Because scope is locked, "priority" here reflects sequencing/risk within the seven days rather than a build/no-build decision — everything below is already committed. High-complexity, high-dependency items belong earlier in the week; low-complexity, late-dependency items belong later.

| Feature | Thesis Value | Implementation Complexity | Sequencing Note |
|---------|--------------|----------------------------|------------------|
| Structured claim schema + evidence validator | HIGH (Law 1 core) | MEDIUM | Early — everything else in Law 1 and much of Law 2 depends on it |
| Deployer sidecar + rollback executor + verification query | HIGH (Law 2 core, and the only real "action" in the whole system) | MEDIUM-HIGH | Early-to-mid — isolation architecture needs to be right before anything depends on it |
| Policy module (six checks) | HIGH (Law 2 core) | MEDIUM-HIGH | Mid — needs both claim-schema outputs and Law 3 telemetry to be real |
| Per-LLM-call instrumentation (tokens/cost/duration) | HIGH (Law 3 base, and cost feeds Incident 2 directly) | LOW-MEDIUM | Early — many downstream features (cost watchdog, dashboard agent-health section, policy SLO check) read from this |
| Loop breaker + cost watchdog | HIGH (Law 3 enforcement) | MEDIUM | Mid — needs per-call instrumentation first |
| Four seeded incidents + fault injection | HIGH (this is what the whole system is demonstrated against) | MEDIUM | Early-to-mid, parallelizable with the agent pipeline since it lives in the monitored app |
| Span links (investigation → incident trace) | MEDIUM-HIGH (differentiator, judging-visible) | MEDIUM-HIGH | Mid-to-late — depends on both the incident traces and the investigation spans existing |
| SigNoz dashboard (four sections) | MEDIUM (judging-visible, but not thesis-critical if late) | MEDIUM | Late — deliberately last, since it aggregates everything else |
| SigNoz alerts (separate from dashboard) | MEDIUM (judging-visible SigNoz depth) | LOW-MEDIUM | Late, parallelizable with dashboard work |
| Foundry `casting.yaml`/`.lock` + clean-machine rebuild | HIGH (submission-level requirement, judging-critical) | MEDIUM | Should be validated continuously, not left to the last day, given the 15-minute rebuild constraint |
| Scripted manual baseline for comparison | MEDIUM (supports the evaluation narrative, not the product itself) | LOW | Late — independent of the agent build, can slot in whenever |

---

## Competitor Feature Analysis

| Dimension | Cleric | Traversal | Datadog Bits AI (Investigation) | SigNoz's own LangChain-MCP post | Agent K (locked scope) |
|-----------|--------|-----------|-----------------------------------|-----------------------------------|--------------------------|
| Multi-signal telemetry | Yes (logs, metrics, traces, recent changes) | Yes (250B log lines/day at reference customer) | Yes (traces, metrics, logs via Datadog) | Yes (via SigNoz MCP) | Yes |
| Ranked/confident hypotheses | Yes, delivered to Slack | Yes — returns candidate causes with confidence rather than a single answer | Yes — posts a final root-cause summary to the incident thread | No RCA hypothesis behavior shown (Q&A only) | Yes — structured claim schema with confidence field |
| Evidence structurally enforced (code deletes unsupported claims) | Not documented | Not documented | Not documented | Not applicable (no claims generated) | **Yes — the core differentiator** |
| Evidence links verified against a live instance | Not documented | Not documented | Not documented | Not applicable | **Yes** |
| Action taken | No (observation/recommendation only) | Not primary focus (causal analysis, not stated as taking actions) | Not the focus of "Investigation" product (root cause, not remediation) | No | Yes — one allowlisted action (rollback), policy-gated |
| Explicit approve/deny evaluation design | Not documented | Not documented | Not documented | Not applicable | Yes — 2 approvals / 2 denials across 4 incidents, 3 runs each |
| Self-observability of the agent's own resource use | Not publicly documented (vendor product, not exposed to customers) | Not publicly documented | Not publicly documented | Partial — dashboard shows p95 latency, token usage, tool distribution, error rate | Full — computed cost, loop detection, budget watchdog that halts investigation |
| Reproducible one-command deployment for third-party verification | Not applicable (SaaS product) | Not applicable (SaaS product) | Not applicable (SaaS product) | Not applicable (blog walkthrough) | Yes — Foundry `casting.yaml`/`.lock`, <15 min clean rebuild |
| Cost-only (no-error-rate) failure scenario staged | Not documented | Not documented | Not documented | Not applicable | Yes — Incident 2 |

**Reading this table:** Agent K does not out-compete the commercial field on breadth (fewer telemetry sources, one action, four scenarios by design) or on scale (four controlled scenarios vs. production fleets processing billions of log lines). Its competitive claims are all about *structural guarantee and auditability* — evidence that can't render unsupported, links that are checked not asserted, a policy gate whose reasoning is itself telemetry, and self-observability that can halt the agent rather than just report on it. That is also exactly where it goes beyond SigNoz's own most-similar published post.

---

## Sources

**SigNoz official / prior art (read in full):**
- [Monitoring a LangChain Agent Querying the SigNoz MCP Server](https://signoz.io/blog/monitoring-langchain-agent-querying-signoz-mcp-server/) — HIGH confidence
- [SigNoz MCP: Log and Trace Investigation](https://signoz.io/blog/signoz-mcp-log-trace-investigation/) — HIGH confidence
- [Introducing Agent-Native Observability](https://signoz.io/blog/introducing-agent-native-observability/) — HIGH confidence

**SigNoz feature documentation:**
- [Alerts | SigNoz Docs](https://signoz.io/docs/alerts/) — HIGH confidence
- [SLO Monitoring guide | SigNoz](https://signoz.io/guides/slo-monitoring/) — MEDIUM-HIGH confidence
- [Implementing Alerts as Code | SigNoz](https://signoz.io/guides/alerts-as-code/) — MEDIUM-HIGH confidence
- [Correlate Traces and Logs | SigNoz Docs](https://signoz.io/docs/traces-management/guides/correlate-traces-and-logs/) — HIGH confidence
- [Trace Details / Span Details panel | SigNoz Docs](https://signoz.io/docs/userguide/span-details/) — HIGH confidence
- [Query Builder v5 guide | SigNoz Docs](https://signoz.io/docs/userguide/query-builder-v5/) — HIGH confidence
- [Dashboards overview | SigNoz Docs](https://signoz.io/docs/dashboards/overview/) — HIGH confidence
- [Interactivity in dashboards | SigNoz Docs](https://signoz.io/docs/dashboards/interactivity/) — MEDIUM confidence (time-shift/deploy-comparison detail)
- [Creating SigNoz Dashboards with Terraform | SigNoz Docs](https://signoz.io/docs/dashboards/terraform-provider-signoz/) — HIGH confidence
- [Creating SigNoz Alerts with Terraform | SigNoz Docs](https://signoz.io/docs/alerts-management/terraform-provider-signoz/) — HIGH confidence
- [SigNoz Terraform provider registry](https://registry.terraform.io/providers/SigNoz/signoz/latest/docs) — HIGH confidence

**Commercial AI-SRE / incident-response competitive landscape (MEDIUM confidence, cross-checked across multiple sources per claim):**
- [awesome-ai-sre (GitHub)](https://github.com/pavangudiwada/awesome-ai-sre) — category taxonomy of ~70+ AI SRE/incident tools
- [Traversal — Agentic AI for Incident Response](https://www.traversal.com/blog/agentic-ai-for-incident-response) — 82% RCA accuracy, 32% MTTR reduction claims (vendor-published)
- [Rootly — AI SRE](https://rootly.com/ai-sre) and [Rootly AI-Driven Incident Response](https://webflow.rootly.com/blog/ai-driven-incident-response-for-sres-best-practices-use-cases-risks-and-mttr-reduction) — confidence-scored parallel hypothesis testing
- [incident.io — Investigations](https://incident.io/investigations) and [incident.io — AI SRE](https://incident.io/ai-sre) — 90% accuracy claim (vendor-published)
- [Datadog — Bits Investigation](https://www.datadoghq.com/product/ai/bits-investigation/) — investigation/root-cause posting to incident thread
- [Choosing an AI SRE Tool: CTO Decision Framework 2026](https://prommer.net/en/tech/guides/best-ai-sre-tools-2026/) — Cleric described as observation/recommendation-only
- [K8sGPT overview (Medium/Squer)](https://medium.com/@yaswanth.arumulla/k8sgpt-bringing-ai-powered-troubleshooting-to-kubernetes-2b1c96e17115) — open-source RCA-adjacent comparison point

**Failure modes / hallucination / safety criticism (MEDIUM confidence):**
- [Your AI Ops Agent Is Guessing (Causely)](https://causely-blog.ghost.io/your-ai-ops-agent-is-guessing/)
- [How to teach SRE AI agents to fail safely (InfoWorld)](https://www.infoworld.com/article/4195114/how-to-teach-sre-ai-agents-to-fail-safely-and-earn-your-teams-trust.html)
- [When AI SRE Fails: Production Reality, Failure Modes, and What They Cost (SoftwareSeni)](https://www.softwareseni.com/when-ai-sre-fails-production-reality-failure-modes-and-what-they-cost/)
- [The 4-body problem of SRE (CNCF)](https://www.cncf.io/blog/2026/07/06/the-4-body-problem-of-sre-why-autonomous-operations-depend-on-context/)
- [Inside the lethal trifecta: Blast radius reduction in AI agent deployments (Sophos)](https://www.sophos.com/en-us/blog/inside-the-lethal-trifecta-blast-radius-reduction-in-ai-agent-deployments)

**Evidence/citation schema patterns (MEDIUM confidence, academic literature):**
- [PaperTrail: A Claim-Evidence Interface for Grounding Provenance in LLM-based Scholarly Q&A](https://arxiv.org/html/2602.21045v1)
- [From Agent Traces to Trust: Evidence Tracing and Execution Provenance in LLM Agents](https://arxiv.org/html/2606.04990v1)
- [Evaluating LLM Citation & Attribution (2026)](https://futureagi.com/blog/evaluating-llm-citation-attribution-2026/) — structural/resolvability/semantic rubric

**Agent self-observability / loop detection / budget guardrails (MEDIUM confidence):**
- [OpenTelemetry blog — Inside the LLM Call: GenAI Observability with OpenTelemetry](https://opentelemetry.io/blog/2026/genai-observability/) — HIGH confidence (official OTel source)
- [Runtime Budget Guardrails for Agentic AI (Oracle)](https://blogs.oracle.com/ai-and-datascience/runtime-budget-guardrails-agentic-ai)
- [Your Agent Is Calling That Tool Again: tool-loop-guard (DEV)](https://dev.to/mukundakatta/your-agent-is-calling-that-tool-again-tool-loop-guard-4n9c) — N=3 warning / N=5 loop threshold convention

---
*Feature research for: AI-powered incident-response/RCA agent (evidence-first, safety-gated), SigNoz Track 01 hackathon submission*
*Researched: 2026-07-20*
