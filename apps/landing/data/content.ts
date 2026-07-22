export const navItems = [
  { label: "The problem", href: "#problem" },
  { label: "Three laws", href: "#laws" },
  { label: "Protocol", href: "#protocol" },
  { label: "Proof", href: "#proof" },
] as const;

export const trustItems = [
  { label: "Every claim", value: "Evidence-linked" },
  { label: "Every action", value: "Policy-gated" },
  { label: "Every decision", value: "Fully traced" },
] as const;

export const investigationSequence = [
  "Alert received",
  "Collect evidence",
  "Constrain cause",
  "Check policy",
  "Act if allowed",
  "Verify recovery",
  "Record everything",
] as const;

export const incidentStages = [
  { title: "Alert received", detail: "Burn rate breached", status: "Alert received. Collecting telemetry." },
  { title: "Evidence collected", detail: "Traces · logs · deploys", status: "3 sources linked. Testing hypotheses." },
  { title: "Cause constrained", detail: "Prompt v2 correlated", status: "Cause supported. Recalibrating confidence." },
  { title: "Policy checked", detail: "6 of 6 rules pass", status: "6 of 6 checks pass. Rollback authorized." },
  { title: "Recovery verified", detail: "Error rate normalized", status: "Recovery verified. Report sealed." },
] as const;

export const incidentEvidence = [
  { kind: "trace", title: "Trace cluster", detail: "31 failed requests" },
  { kind: "log", title: "Error logs", detail: "Template mismatch" },
  { kind: "deploy", title: "Deploy marker", detail: "v2 · 09:55 UTC" },
] as const;

export const laws = [
  {
    number: "01",
    key: "evidence",
    label: "Evidence",
    title: "No claim without proof.",
    description: "A root-cause claim can't appear unless resolvable telemetry backs it. No evidence, no published claim.",
    checks: [
      ["Claim + confidence", "Required"],
      ["Query + time range", "Attached"],
      ["Evidence link", "Verified"],
    ],
  },
  {
    number: "02",
    key: "policy",
    label: "Policy",
    title: "No action without permission.",
    description: "The model suggests. Only deterministic policy authorizes. One check fails, Agent K stops and escalates.",
    checks: [
      ["Allowlisted action", "Rollback only"],
      ["SLO + confidence", "Checked"],
      ["Cooldown + sandbox", "Enforced"],
    ],
  },
  {
    number: "03",
    key: "telemetry",
    label: "Telemetry",
    title: "No self without a trace.",
    description: "The investigator is observable too. Cost, duration, loops, queries, confidence, every verdict — all part of the audit trail.",
    checks: [
      ["Token + cost budget", "Visible"],
      ["Query loop breaker", "Active"],
      ["Every verdict", "Traced"],
    ],
  },
] as const;

export const protocolSteps = [
  {
    number: "01",
    key: "signal",
    label: "Signal",
    title: "An alert becomes a case.",
    description: "Agent K receives the incident and opens a traceable investigation. No action path exists yet.",
  },
  {
    number: "02",
    key: "observe",
    label: "Observe",
    title: "Telemetry, gathered with a trail.",
    description: "Traces, metrics, logs, alerts, and deploy markers collected through one observable path.",
  },
  {
    number: "03",
    key: "reason",
    label: "Reason",
    title: "Causes compete on evidence.",
    description: "The model proposes a hypothesis. Code recalibrates confidence from the proof actually attached.",
  },
  {
    number: "04",
    key: "govern",
    label: "Govern",
    title: "Policy decides. Not probability.",
    description: "Six deterministic checks return ALLOW or DENY. The model never gets a vote at this boundary.",
  },
  {
    number: "05",
    key: "verify",
    label: "Verify",
    title: "Recovery measured. Record sealed.",
    description: "Agent K re-queries the system after action and publishes an auditable report: success, denial, or escalation.",
  },
] as const;

export const proofEvidence = [
  { type: "TRACE", title: "31 failed requests", detail: "09:55–10:15 UTC · trace cluster" },
  { type: "LOG", title: "Prompt variable mismatch", detail: "correlated by trace ID" },
  { type: "DEPLOY", title: "support-api v2 marker", detail: "6 min before first failure" },
] as const;

export const policyChecks = [
  "SLO breach confirmed",
  "Rollback allowlisted",
  "Cooldown passed",
  "Confidence ≥ threshold",
  "Deployment-related cause",
  "Sandbox scope confirmed",
] as const;

export const evaluationMetrics = [
  { value: "4 / 4", label: "Controlled diagnoses", note: "target" },
  { value: "12", label: "Documented runs", note: "planned" },
  { value: "100%", label: "Evidence links resolve", note: "target" },
  { value: "0", label: "Actions outside policy", note: "required" },
] as const;

export const illustrativeQuery = 'service.name = "support-api" AND status = "error" AND deployment.version = "v2"';
