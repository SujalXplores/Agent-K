# Feature Research

**Domain:** AI incident-response agent / AIOps / agent-observability (code-enforced safety, evidence-backed RCA)
**Researched:** 2026-07-20
**Confidence:** MEDIUM (vendor blogs/docs cross-checked across 2+ independent sources per claim; some 2026 "trend roundup" aggregator sites downgraded to LOW and flagged inline)

**Scope note:** Agent K's feature set is already locked in `.planning/PROJECT.md`. This document does not propose new features — it validates the locked set against what real AI-incident-response products ship, sorts the locked set into table-stakes / differentiator / anti-feature, and flags coherence gaps that stay *inside* the existing lock.

## Feature Landscape

### Table Stakes (Users Expect These)

These are non-negotiable for the "incident-response agent" framing to hold up — all already present in Agent K's locked scope. Confirmed present in Datadog Bits AI SRE, Honeycomb AI-assisted investigations, PagerDuty AIOps, and incident.io AI SRE.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Alert ingestion (webhook → agent) | Every competitor triggers investigation from a fired alert, not a manual chat prompt. Datadog Bits and PagerDuty both auto-launch on alert. | LOW | Already locked: SigNoz webhook → Agent K HTTP endpoint. |
| Iterative hypothesis-driven investigation loop | Datadog Bits explicitly runs an "observe-reason-act" loop: form hypothesis → query telemetry → validate/invalidate → refine, chaining steps until convergence. Honeycomb's AI-assisted investigations do the same via NLQ + notebook. Users expect an agent that *investigates*, not one that pattern-matches once. | MEDIUM | Matches Agent K's state-machine investigation loop exactly. |
| Structured final artifact, not a chat transcript | 2026 AI-SRE consensus (multiple independent sources): agent must emit a final artifact — summary + evidence chain + suggested remediation — rather than a raw conversation log. incident.io enforces this via LLM JSON-mode with required Problem/Impact fields. | MEDIUM | Matches Agent K's structured claim schema + HTML report renderer. |
| Deployment/change correlation | Datadog Bits' flagship root-cause example traces an alert back through a deployment/config change. Change-correlation is the single most common root-cause pattern across all four vendors researched. | MEDIUM | Matches Agent K's deployment markers + prompt-regression scenario. |
| Evidence attached to claims (some form of citation) | incident.io's AI SRE differentiates itself from pure summarizers specifically by citing PRs/data sources per claim. Table-stakes floor is "cite something"; Agent K's floor is higher (see differentiators). | LOW–MEDIUM | Locked scope already exceeds table-stakes floor here — see Law 1 below. |
| Human escalation when agent can't safely conclude/act | Cross-vendor consensus: human stays in the loop for scope/trust/postmortem decisions; agents hand off with partial findings rather than guessing. | LOW | Matches Agent K's loop-breaker → "escalates to human with partial evidence." |
| Action audit trail | Guardrail literature (Reco, Galileo, isimplify.me sources) treats audit logs as a baseline safety requirement, not a nice-to-have, for any agent that can act. | LOW–MEDIUM | Matches Agent K's dashboard "action audit trail" section + Law 3 policy-decision logging. |

### Differentiators (Competitive Advantage)

These map to Agent K's "Three Laws" framing and are where Agent K should be *proud* to differ from Datadog/PagerDuty/incident.io, not apologetic about smaller scope.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Code-enforced evidence gate (Law 1: link checker + claim-stripping renderer) | Every vendor researched *cites* evidence via LLM prompting (incident.io shows PRs, Datadog shows telemetry snippets) but none was found to run a deterministic, non-LLM check that every published claim's evidence link actually resolves against the live system before it's shown. This is Agent K's sharpest wedge: "prove-it-in-telemetry" is enforced by code, not by asking the model nicely. | HIGH | Directly maps to Core Value in PROJECT.md. Requires MCP integration + span-link plumbing to exist first (dependency). |
| Deterministic, non-LLM policy gate before any action (Law 2) | Industry pattern is "human approval button in a UI" — the *decision to ask* is still often inside the agent's own reasoning. Agent K's policy module (SLO breach, allowlist, cooldown, confidence threshold, deployment-relatedness, sandbox scope) sits in plain code, separate from the LLM, and is itself demoable/inspectable. Matches the "rule-based gate vs risk-based gate" distinction from guardrail research — Agent K commits fully to rule-based, which is more auditable than a model-scored risk gate. | MEDIUM–HIGH | Single allowlisted action keeps this tractable in 7 days; a broader action catalog (like PagerDuty's) would not be. |
| Verified-outcome rollback (re-query SigNoz to confirm recovery, record result) | Common pattern elsewhere is "execute remediation, assume success." Agent K closes the loop: act → wait → re-query → record outcome. This is a small implementation delta with outsized credibility payoff for the "would people adopt this" judging criterion. | MEDIUM | Depends on Law 2 approving the action first. |
| Agent self-telemetry as a first-class, demoable product surface (Law 3) | The closest industry analog (Honeycomb Agent Timeline/Canvas Skills) is brand-new (2025-2026) and is a generic dev-tool feature, not something bolted onto an incident-response agent's own operational dashboard. Cost/loop-count/hypothesis-count telemetry is usually invisible to end users of AIOps tools; Agent K makes the agent's own behavior a graded, visible dashboard section — "the investigator is investigated." | MEDIUM–HIGH | Must be instrumented *into* the state machine as it's built, not added after (see dependencies). |
| Loop breaker + cost watchdog as visible, demoable safety features | Research confirms "token spike = first sign of a loop" is known best practice, but it's rarely productized as something a judge/user can *watch happen* live. Toggling a failure scenario and watching the watchdog fire is a strong demo beat. | MEDIUM | Depends on Law 3 telemetry (query hashing, cost tracking) being live. |
| Hybrid confidence scoring (LLM proposes, code recalibrates) | No vendor researched was found to recalibrate a model's self-reported confidence against hard evidence signals (deployment marker present, error-rate delta magnitude, etc.). Most either trust the model's stated confidence or use a separate black-box risk score. Agent K's recalibration is itself auditable. | MEDIUM | Consumes Law 1 evidence data as recalibration input (dependency). |

### Anti-Features (Commonly Requested, Often Problematic)

Cross-validated against what Datadog/PagerDuty/incident.io/Honeycomb actually build — these reinforce Agent K's existing Out of Scope list. Do not add any of these even if they look "obviously good."

| Feature | Why Requested | Why Problematic (for Agent K specifically) | Alternative |
|---------|---------------|------------------------------------------|-------------|
| Multi-channel notification/collaboration integrations (Slack, Teams, Jira, ServiceNow paging) | Every major vendor (Datadog: 7 triage actions incl. Slack/Teams/Jira; PagerDuty: native paging; incident.io: Slack-native) ships this, so it "looks like" table stakes. | Zero-budget + 7-day constraint; adds integration surface with no judging-criteria payoff (SigNoz depth and safety-gating are what's judged, not Slack polish). Already excluded via "no general chatbot/dashboard-with-chat-box" anti-goal. | The HTML report page + SigNoz dashboard *is* the interface; human finds it there. |
| Alert correlation/dedup/grouping across many noisy alerts | PagerDuty's core AIOps value prop is "91% alert reduction" via grouping — looks like the obvious next feature for "AIOps." | Agent K has exactly 4 seeded incident types firing one at a time in a demo; building a noise-reduction/correlation engine solves a problem Agent K doesn't have and dilutes the single-incident evidence story. | None needed — out of scope stays out of scope. |
| Expanding the remediation action catalog / runbook library | PagerDuty Runbook Automation and Datadog's Action Catalog both push toward *more* actions over time — natural instinct is "why only one action?" | The single-allowlisted-action constraint is the entire point of Law 2's safety story; adding actions multiplies the attack surface for an ungoverned action in a system built by a team with zero prior DevOps experience, in 7 days. | Keep exactly one action (rollback); the *policy gate*, not the action catalog, is what's being showcased. |
| Fully autonomous "no human ever needed" remediation | Industry trend language ("autonomously resolve issues," Datadog/PagerDuty marketing) makes full autonomy sound like the finish line. | Undermines the safety-first pitch and the honesty commitment ("4/4 on four controlled scenarios," no production-readiness claims). Progressive-autonomy research explicitly says trust should expand only after a failure class proves reliable — Agent K hasn't earned that yet by design. | Keep action gated behind Law 2 every single time; never bypass the policy check for "obviously safe" cases. |
| General-purpose chat/Q&A interface over telemetry (à la Honeycomb Query Assistant/Canvas) | Natural-language querying is a flashy, demoable AI feature and genuinely useful in Honeycomb's product. | Explicit anti-goal already stated in PROJECT.md: "Agent K is an evidence-producing workflow, not a Q&A bot." Adding a chat box would blur the "workflow, not chatbot" positioning that differentiates the pitch. | Structured report + dashboard only; no freeform query surface. |
| Cross-service/dependency-graph root-causing (Datadog's multi-hop dependency tracing) | Looks like "deeper" root-cause analysis, and dependency graphs are visually impressive. | Agent K is a single FastAPI app with one datastore — there is no dependency graph to trace. Building this would require infrastructure (K8s, service mesh) explicitly out of scope. | The four seeded scenarios are single-service by design; root-cause chains stay within the one app + its two dependencies (DB, LLM provider). |

## Feature Dependencies

```
SigNoz MCP integration (direct SDK calls from state machine)
    └──requires──> Investigation loop (state machine)
                       └──requires──> Structured claim schema (Law 1)
                                          └──requires──> Evidence link checker
                                          └──requires──> Confidence scoring (LLM propose)
                                                             └──requires──> Confidence recalibration (code, uses evidence strength/count)
                                                                                └──requires──> Law 2 policy gate (confidence threshold is one check)

Law 2 policy gate (SLO breach, allowlist, cooldown, confidence, deployment-relatedness, sandbox scope)
    └──requires──> Action caller (single allowlisted action; one authenticated HTTP POST)
                       └──requires──> Deployer sidecar (POST /rollback, sole Docker-socket holder,
                                        privilege-isolated from Agent K)
                       └──requires──> Verified-outcome recheck (re-query SigNoz post-action)

Investigation loop
    └──requires──> Law 3 self-telemetry instrumented inline (not bolted on after)
                       └──enables──> Loop breaker (query hash repeats)
                       └──enables──> Cost watchdog (token/cost budget)
                       └──enables──> Escalation-with-partial-evidence path

All of: RAG app OTel instrumentation + Law 1 evidence spans + Law 3 self-telemetry + Law 2 action audit
    └──feeds──> SigNoz dashboard (4 sections: service health, incident context, agent health, action audit trail)

Structured claim schema + evidence link checker
    └──feeds──> HTML incident report page (report renderer strips claims with empty evidence)

Deployment markers (every version change, incl. flag-triggered "deployments")
    └──enables──> Deployment-related-cause check inside Law 2 policy
    └──enables──> Datadog-style "trace alert back to deploy" root-cause pattern (Incident 1: prompt-regression)

Four seeded failure scenarios (feature-flag service)
    └──requires──> Nothing upstream (independent) but is the trigger source for every downstream Law
```

### Dependency Notes

- **Law 1 requires MCP integration first:** the evidence schema is meaningless without live, individually-visible SigNoz queries to cite — this is why MCP wiring must land early in the roadmap, not alongside the report page.
- **Confidence recalibration requires Law 1 evidence data:** the code-side recalibration inputs (deployment marker present, error-rate delta magnitude) *are* Law 1 evidence fields — these two features must be built in the same phase or recalibration has nothing to consume.
- **Law 2 requires confidence scoring + deployment markers + Law 1 evidence:** the policy gate checks span multiple upstream features; it cannot be built before any of them exist, and is naturally a later-phase feature.
- **Law 3 self-telemetry should be instrumented inline, not bolted on:** because the locked scope requires per-LLM-call, per-MCP-query, per-hypothesis telemetry, retrofitting this after the investigation loop is built means re-touching every code path. Roadmap should treat "instrument as you go" as a standing constraint on the investigation-loop phase, not a separate later phase.
- **Loop breaker and cost watchdog enhance the investigation loop but depend on Law 3 telemetry being live:** query hashing and cost tracking are Law 3 outputs; the breakers just consume them.
- **Dashboard is a terminal dependency, not a starting point:** all four dashboard sections pull from telemetry that must already exist (app OTel, Law 1 spans, Law 3 metrics, Law 2 audit events) — it should be one of the last things built, consistent with existing Key Decisions.
- **Rollback requires Law 2 approval as a hard gate, and its own success/failure is itself Law 3 telemetry** — the action path and Law 3 are mutually reinforcing (action feeds telemetry, telemetry feeds audit trail).
- **Rollback executes through a privilege-isolated deployer sidecar, not from Agent K itself:** the sidecar (a separate process that is the sole holder of the Docker socket, exposing one authenticated `POST /rollback`) must be stood up and network-reachable before the action path can be tested end-to-end. Agent K never holds the Docker socket — that isolation is precisely what makes Law 2's "inside the sandbox" check structural rather than cosmetic. The sidecar has no dependency on Agent K's reasoning pipeline, so it can be scaffolded and smoke-tested early to de-risk the most safety-critical component.

## MVP Definition

Scope is locked; there is no "cut features" MVP tier here. Instead, this reframes the locked set by demo-criticality within the fixed 7-day window — useful for phase sequencing, not for scope negotiation.

### Demo-Critical (must work for judging — v1)

- [ ] Alert ingestion via SigNoz webhook — without this there is no live-triggered investigation to show.
- [ ] Investigation loop producing at least one evidence-backed claim per seeded incident — this *is* the product.
- [ ] Law 1 link checker showing 100% evidence resolution — directly judged ("deepest SigNoz integration," evidence-integrity constraint).
- [ ] Law 2 policy gate + single rollback action, demoed both approving and denying — the safety-first pitch has no proof without a visible deny case, not just an approve case.
- [ ] Law 3 telemetry visible on the dashboard (cost, loop count, action audit) — the "self-observed" half of the pitch is invisible without this.
- [ ] HTML incident report with clickable SigNoz deep links — this is the artifact judges will actually read.
- [ ] One polished 4-section dashboard — explicitly required, judged directly.

### Depth Add-Ons (strengthens scoring, not required for the demo path to function)

- [ ] All four seeded incidents demoed live in sequence (vs. one or two well-polished ones) — depends on time remaining after demo-critical path is solid.
- [ ] Evaluation harness full 3-runs-per-incident report (12 runs) with honest failure reporting — strengthens "technical excellence" and "presentation" criteria but the core demo can proceed on fewer runs if time is short.
- [ ] Loop-breaker/cost-watchdog *live* trigger during the demo (not just present in code) — high demo value but riskier to stage live; have a recorded fallback.

### Explicitly Still Out of Scope (not a future v2 backlog — reinforces existing PROJECT.md exclusions)

- [ ] Multi-channel notifications (Slack/Jira/ServiceNow) — stays excluded per anti-features table above.
- [ ] Expanded action catalog beyond the one rollback action — stays excluded; this is a safety-story constraint, not a time constraint.
- [ ] Alert correlation/noise reduction across many concurrent alerts — stays excluded; no scenario in the locked scope needs it.

## Feature Prioritization Matrix

Within the already-locked scope, prioritized by the two judging criteria named in `<research_type>`: "deepest possible SigNoz integration" and "would people actually adopt this."

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SigNoz MCP integration (direct SDK, every query visible) | HIGH | MEDIUM | P1 |
| Law 1 evidence schema + link checker | HIGH | HIGH | P1 |
| Investigation loop / hypothesis generation | HIGH | MEDIUM | P1 |
| Law 2 policy gate + single rollback action | HIGH | MEDIUM–HIGH | P1 |
| Law 3 self-telemetry (inline instrumentation) | HIGH | MEDIUM–HIGH | P1 |
| 4-section SigNoz dashboard | HIGH | MEDIUM | P1 |
| HTML incident report page | MEDIUM–HIGH | LOW–MEDIUM | P1 |
| Confidence recalibration (hybrid) | MEDIUM | MEDIUM | P2 |
| Loop breaker + cost watchdog | MEDIUM–HIGH | MEDIUM | P2 |
| Verified-outcome rollback recheck | MEDIUM | LOW | P2 |
| Evaluation harness (3 runs × 4 incidents) | MEDIUM | MEDIUM | P2 |
| Deployment markers on every version change | MEDIUM | LOW | P2 |
| Alerts hand-built separately from dashboard | LOW–MEDIUM | LOW | P3 |
| Submission blog with honest results | HIGH (for judging "presentation") | LOW | P3 (do last, needs real data) |

**Priority key:**
- P1: Demo-critical — must work for the pitch to hold together.
- P2: Should have — differentiates and strengthens judged criteria, build if the P1 path is on schedule.
- P3: Necessary but low-risk/low-effort — sequence late, not blocking.

## Competitor Feature Analysis

| Feature axis | Datadog Bits AI SRE | PagerDuty AIOps | incident.io | Honeycomb | Agent K's Approach |
|---------------|---------------------|------------------|-------------|-----------|---------------------|
| Investigation pattern | Continuous observe-reason-act loop over telemetry, converges on root cause before humans log in | Cross-stack signal gathering + diagnostics + similar-incident comparison | LLM-summarized timeline + PR/data-source citations for root cause | Natural-language question → auto query/trace/visualize, presented as an interactive notebook | Plain-Python state machine looping SigNoz MCP queries per hypothesis, no framework — same pattern, deliberately un-black-boxed |
| Evidence for claims | Shows telemetry/runbook evidence in conclusion, not independently link-checked (per sources reviewed) | Compares to similar past incidents; evidence depth not detailed in sources reviewed | Cites specific PRs/data sources per claim (LLM-prompted, not code-verified) | Query results + visualizations shown inline in notebook | Structured claim schema with evidence[]; **code-enforced link checker strips any claim whose evidence doesn't resolve** — highest rigor of the set |
| Remediation action scope | 7 triage actions + expanding Action Catalog (Trigger/Get/List Investigation) — broad and growing | Recommends + executes remediation "with human approval"; also full Runbook Automation library | Not primarily an actor — mostly investigate/summarize | Not a remediation product — investigation-focused | Exactly one allowlisted action (rollback), gated by deterministic code policy, not LLM judgment — narrowest and most auditable of the set |
| Safety gate mechanism | Not fully detailed in sources reviewed; implied approval workflows via Case Management/Incident Response | Human-approval step before automated execution (approval UI, not necessarily code-external policy) | N/A (limited remediation) | N/A (no remediation) | Separate, non-LLM policy module (SLO breach, allowlist, cooldown, confidence threshold, deployment-relatedness, sandbox scope) — policy logic lives outside the model entirely |
| Agent self-observability | Not surfaced as a user-facing feature in sources reviewed | Not surfaced as a user-facing feature in sources reviewed | Not surfaced as a user-facing feature in sources reviewed | Closest analog: Agent Timeline / Canvas Agent / Canvas Skills (2025-2026, generic dev-tool feature) | First-class dashboard section: agent's own cost/loop-count/hypothesis-count/policy-decisions, purpose-built for *this* agent, not a generic add-on tool |
| Audit trail | Delivers conclusions to collaboration tools (Slack/Teams/Jira) — trail lives across third-party tools | Learns from every response ("smart runbooks") — audit depth not detailed | Structured JSON-mode summaries stored in-platform | Canvas retains collaborative session history | Dedicated dashboard section (action audit trail) + span links from investigation to incident traces, all inside SigNoz — single source of truth, no third-party trail fragmentation |
| Collaboration/notification surface | Native mobile app, On-Call, Case Management synced to ServiceNow/Jira, Slack/Teams | Deep paging/on-call integration (core PagerDuty product) | Slack-native, built on top of incident channels | Multi-user Canvas sessions | Deliberately none — HTML report page + SigNoz dashboard only (anti-feature, see table above) |

## Sources

- [Bits Investigation | Datadog](https://www.datadoghq.com/product/ai/bits-ai-sre/)
- [Introducing Bits Investigation, your AI on-call teammate | Datadog](https://www.datadoghq.com/blog/bits-ai-sre/)
- [Meet the new Bits Investigation: Deeper reasoning, twice as fast | Datadog](https://www.datadoghq.com/blog/bits-ai-sre-deeper-reasoning/)
- [Bits AI Agents | Datadog](https://www.datadoghq.com/product/ai/bits-ai-agents/)
- [Datadog Launches Bits AI SRE Agent to Resolve Incidents Faster](https://www.datadoghq.com/about/latest-news/press-releases/datadog-launches-bits-ai-sre-agent-to-resolve-incidents-faster/)
- [Investigate Issues | Datadog Docs](https://docs.datadoghq.com/bits_ai/bits_ai_sre/investigate_issues/)
- [Honeycomb: AI-Ready Observability Platform](https://www.honeycomb.io/)
- [Observability, Meet Query Assistant, NLQ in Honeycomb](https://www.honeycomb.io/blog/introducing-query-assistant)
- [Honeycomb Intelligence | AI-Powered Observability Platform](https://www.honeycomb.io/platform/intelligence)
- [Honeycomb Canvas | AI-guided Observability Workspace](https://www.honeycomb.io/platform/canvas)
- [Find and Debug Issues Easily with Observability | Honeycomb](https://www.honeycomb.io/use-cases/incident-response)
- [AIOps | PagerDuty](https://www.pagerduty.com/platform/aiops/)
- [PagerDuty AIOps Docs](https://support.pagerduty.com/main/docs/aiops)
- [Automation | PagerDuty](https://www.pagerduty.com/platform/automation/)
- [AIOps Use Cases for Faster Incident Resolution | PagerDuty](https://www.pagerduty.com/resources/aiops/learn/aiops-use-cases-incident-resolution/)
- [PagerDuty Operations Cloud Spring 25 Release](https://www.pagerduty.com/blog/product/product-launch-enhancements-to-pagerduty-operations-cloud-2025-h1/)
- [5 best AI-powered incident management platforms 2026 | incident.io](https://incident.io/blog/5-best-ai-powered-incident-management-platforms-2026)
- [Incident.io: Building and Deploying an AI-Powered Incident Summary Generator | ZenML LLMOps Database](https://www.zenml.io/llmops-database/building-and-deploying-an-ai-powered-incident-summary-generator)
- [Adding Guardrails for AI Agents: Policy and Configuration Guide | Reco](https://www.reco.ai/hub/guardrails-for-ai-agents)
- [Essential Framework for AI Agent Guardrails | Galileo](https://galileo.ai/blog/ai-agent-guardrails-framework)
- [AI Agent Audit Trails: Proving What Agents Decided](https://isimplifyme.com/blog/agent-audit-trails)
- [AI Agent Audit Trails Explained | miniOrange](https://www.miniorange.com/blog/ai-agent-audit-trail/)
- [AI Agent Observability: What to Log, Monitor, and Escalate in Production | getagentid.com](https://www.getagentid.com/resources/ai-agent-observability)
- [Token Usage: Tracking and Controlling AI Agent Cost | Prefactor](https://prefactor.tech/learn/token-usage)
- [AI Agent Observability Guide: Telemetry, Traces, Metrics, and Evals | groundcover](https://www.groundcover.com/learn/observability/ai-agent-observability)

*Note: sources for the "2026 AI SRE table stakes consensus" question (aggregator/roundup sites such as xdevops-ai atlas, sherlocks.ai, novaaiops.com) are marked LOW confidence individually — treated here only where their claims cross-corroborate the higher-confidence vendor-primary sources above.*

## Gaps to Flag for Requirements (within existing lock — not scope changes)

These are coherence gaps surfaced by comparing the locked spec against how real products close the same loops. None require adding a feature outside the Active list — they are clarifications the requirements/roadmap phase should resolve explicitly rather than leave implicit.

1. **Passive vs. active human escalation.** The locked spec has the loop-breaker "escalate to human with partial evidence," but every competitor researched pushes an active notification (Slack/page/email) the moment human judgment is needed. Agent K's model is necessarily passive (HTML report + dashboard, no notification channel — correctly out of scope for budget/time reasons). Requirements should state explicitly that "escalation" means *the report/dashboard reflects an incomplete/needs-human state*, not that a human is proactively paged — so the demo script and eval harness don't accidentally assume paging exists.
2. **Report history vs. single latest report.** The spec describes "a small FastAPI-served HTML report page rendering the JSON RCA report" in the singular. With 4 seeded incidents × 3 eval runs = 12 investigations expected, and a dashboard "action audit trail" section that implies multiple historical actions, requirements should clarify whether the report page lists/links multiple past incident reports (by incident ID) or only ever shows the most recent — this affects both the eval harness's ability to reference specific runs and the dashboard's audit-trail credibility.
3. **Denied-action visibility.** Law 3's locked telemetry list already includes "actions attempted/approved/denied," which covers the *data*, but requirements should confirm the dashboard's audit-trail section is designed to make a **denied** action just as visible/demoable as an approved one — a denial is actually the stronger safety-story beat (proves the gate isn't rubber-stamping) and should not be an afterthought relative to the approved-rollback path.

---
*Feature research for: AI incident-response agent / AIOps (Agent K)*
*Researched: 2026-07-20*
