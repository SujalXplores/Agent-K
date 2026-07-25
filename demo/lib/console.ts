/**
 * Console vocabulary: what each demo control does and what Agent K should be
 * expected to conclude.
 *
 * The `expected` fields exist so the console can show expected-vs-actual rather
 * than just "here is an answer". A demo that only shows the happy path proves
 * less than one that states its prediction first and is visibly checkable —
 * including when the model gets the diagnosis wrong, which the recorded eval
 * runs show it sometimes does.
 */

export type ScenarioSpec = {
  id: string;
  label: string;
  blurb: string;
  /** Customer-visible symptom, shown in the help centre's incident strip. */
  symptom: string;
  deployment: boolean;
  expectedVerdict: "approved" | "denied";
  /** Why the gate should land that way — the teaching point of the scenario. */
  because: string;
};

export const SCENARIO_SPECS: ScenarioSpec[] = [
  {
    id: "prompt_regression",
    label: "Prompt regression",
    blurb: "A bad prompt template ships. Answers stop being grounded in retrieved docs.",
    symptom: "Answers lose their grounding and stop citing sources",
    deployment: true,
    expectedVerdict: "approved",
    because:
      "Deployment-caused and inside the sandbox, so all six checks pass and the one allowlisted action runs.",
  },
  {
    id: "retry_storm",
    label: "Retry storm",
    blurb: "Timeouts drop, so every call retries. Latency and token spend climb together.",
    symptom: "Replies crawl as the service retries the model repeatedly",
    deployment: true,
    expectedVerdict: "approved",
    because: "Also deployment-caused — a rollback is a legitimate remedy, so the gate approves.",
  },
  {
    id: "retrieval_latency",
    label: "Retrieval latency",
    blurb: "pgvector search slows down. No error rate change — latency only.",
    symptom: "Noticeable delay before the assistant starts answering",
    deployment: false,
    expectedVerdict: "denied",
    because:
      "No deployment marker exists, so deployment_related fails. Rolling back could not fix an infra fault, and the gate refuses to try.",
  },
  {
    id: "db_pool_exhaustion",
    label: "DB pool exhaustion",
    blurb: "The connection pool starves. Requests fail outright with 500s.",
    symptom: "Requests fail outright once the connection pool is starved",
    deployment: false,
    expectedVerdict: "denied",
    because:
      "An unsupported failure type with no deployment marker — denied, and escalated to a human with the evidence attached.",
  },
];

/** The six deterministic checks in app/policy.py, in the order the gate runs them. */
export const POLICY_CHECKS = [
  { id: "slo_breach", label: "SLO / burn rate breached" },
  { id: "action_allowlisted", label: "Action on the allowlist" },
  { id: "cooldown_elapsed", label: "Cooldown elapsed" },
  { id: "confidence_sufficient", label: "Confidence above threshold" },
  { id: "deployment_related", label: "Cause is deployment-related" },
  { id: "within_sandbox", label: "Target inside the sandbox" },
] as const;

export type GuardrailSpec = {
  id: "loop_breaker" | "cost_budget";
  label: string;
  blurb: string;
  /** The env var a demo tightens to make this guardrail genuinely fire. */
  envVar: string;
  demoValue: string;
};

export const GUARDRAIL_SPECS: GuardrailSpec[] = [
  {
    id: "loop_breaker",
    label: "Loop breaker",
    blurb:
      "Stops an investigation that keeps issuing the same SigNoz query, marks it incomplete and escalates with partial evidence.",
    envVar: "AGENT_K_LOOP_BREAKER_THRESHOLD",
    demoValue: "0",
  },
  {
    id: "cost_budget",
    label: "Cost watchdog",
    blurb:
      "Stops an investigation whose token spend passes its budget, rather than letting cost run while it keeps guessing.",
    envVar: "AGENT_K_TOKEN_BUDGET",
    demoValue: "1",
  },
];
