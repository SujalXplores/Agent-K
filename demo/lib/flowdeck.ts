/**
 * Flowdeck brand + demo constants.
 *
 * Flowdeck is the fictional B2B SaaS product that the monitored RAG service's
 * corpus (`data/corpus/`, 72 hand-authored docs) is written about. This app is
 * Flowdeck's customer-facing help centre — the surface a real user would touch,
 * and therefore the surface that visibly degrades when Agent K's seeded failure
 * scenarios are switched on.
 */

export const BRAND = {
  name: "Flowdeck",
  product: "Flowdeck Support",
  tagline: "Boards, tasks and automations for teams that ship.",
  assistant: "Flowdeck Assistant",
} as const;

/**
 * Starter questions. Every one of these is answerable from the real seeded
 * corpus, so the demo never depends on the model inventing Flowdeck features:
 *   - rotate-api-key.md             (authentication-api-keys)
 *   - error-429-rate-limited.md     (troubleshooting-error-codes)
 *   - sso-saml-setup.md             (authentication-api-keys)
 *   - slack-notifications-stopped-working.md (integrations)
 */
export const SUGGESTED_QUESTIONS: readonly string[] = [
  "How do I rotate an API key?",
  "Why am I seeing error 429?",
  "How do I set up SAML SSO?",
  "Slack notifications stopped working",
];

/**
 * The four seeded failure scenarios (app/flags.py FLAG_NAMES), with the
 * customer-visible symptom each one produces. `deployment` mirrors
 * DEPLOYMENT_CLASS_FLAGS — the two scenarios that emit a deployment marker and
 * are therefore the only ones Law 2's policy gate can approve a rollback for.
 */
export const SCENARIOS: Record<string, { label: string; symptom: string; deployment: boolean }> = {
  prompt_regression: {
    label: "Prompt regression",
    symptom: "Answers lose their grounding and stop citing sources",
    deployment: true,
  },
  retry_storm: {
    label: "Retry storm",
    symptom: "Replies crawl as the service retries the model repeatedly",
    deployment: true,
  },
  retrieval_latency: {
    label: "Retrieval latency",
    symptom: "Noticeable delay before the assistant starts answering",
    deployment: false,
  },
  db_pool_exhaustion: {
    label: "DB pool exhaustion",
    symptom: "Requests fail outright once the connection pool is starved",
    deployment: false,
  },
};

export const FLAG_NAMES = Object.keys(SCENARIOS);
