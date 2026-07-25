/**
 * Server-only client for Agent K's own control and reporting surface.
 *
 * Separate from lib/rag.ts on purpose: that module is the *customer* path
 * (POST /ask), this one is the *operator* path — flags, alerts, investigations.
 * They happen to live on the same FastAPI service, but conflating them would
 * make it easy to accidentally expose an operator control to the help centre.
 */

import { FLAG_NAMES } from "@/lib/flowdeck";

/** One investigation record from GET /api/investigations (app/report.py). */
export type Investigation = {
  id: string;
  state: string;
  status: string;
  incomplete: boolean;
  alertname: string;
  service: string;
  started_at: string;
  incident_type: string | null;
  verdict: string | null;
  failed_checks: string[];
  confidence: number | null;
  action_status: string | null;
  action_verified: boolean | null;
  claims: { claim: string; confidence: number }[];
  mcp_query_count: number;
  mcp_query_failures: number;
  total_tokens: number;
  duration_s: number | null;
  watchdog_events: { kind: string; [k: string]: unknown }[];
};

function baseUrl(): string {
  return (process.env.RAG_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

function adminHeaders(): Record<string, string> {
  const token = process.env.ADMIN_TOKEN;
  return {
    "Content-Type": "application/json",
    // app/flags.py leaves /admin/flags unauthenticated when ADMIN_TOKEN is
    // unset, which is the documented local-demo mode. Sending an empty header
    // would be worse than sending none.
    ...(token ? { "X-Admin-Token": token } : {}),
  };
}

/** Set exactly one scenario on and all others off, so state is unambiguous. */
export async function setOnlyScenario(active: string | null): Promise<void> {
  for (const name of FLAG_NAMES) {
    const response = await fetch(`${baseUrl()}/admin/flags`, {
      method: "POST",
      headers: adminHeaders(),
      body: JSON.stringify({ name, enabled: name === active }),
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(
        `could not set flag ${name}: ${response.status} ${await response.text().catch(() => "")}`,
      );
    }
  }
}

/**
 * Put real traffic through /ask so the incident has telemetry behind it.
 *
 * Failures are swallowed deliberately: under db_pool_exhaustion these requests
 * are *meant* to fail, and that failure is the signal. Throwing here would
 * abort the scenario before the alert ever fired.
 */
export async function generateTraffic(count = 3): Promise<number> {
  const questions = [
    "How do I rotate an API key?",
    "Why am I seeing error 429?",
    "How do I set up SAML SSO?",
  ];
  let ok = 0;
  for (let i = 0; i < count; i++) {
    try {
      const response = await fetch(`${baseUrl()}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: questions[i % questions.length] }),
        cache: "no-store",
      });
      if (response.ok) ok++;
    } catch {
      // intentional: see above
    }
  }
  return ok;
}

/**
 * Fire an Alertmanager-shaped alert webhook, starting an investigation.
 *
 * The envelope matches app/alerts_webhook.py's AlertmanagerWebhookPayload, which
 * requires top-level `receiver` and `status` as well as `alerts` — omitting them
 * is a 422, not a lenient parse. Kept identical in shape to what
 * scripts/run_eval.py posts so a console run and an eval run exercise the same
 * code path rather than two subtly different ones.
 *
 * `startsAt` uses a whole-second Z format rather than toISOString()'s
 * milliseconds, matching the harness — the investigation freezes its evidence
 * time window from this value, so the format is load-bearing, not cosmetic.
 */
export async function fireAlert(scenario: string): Promise<void> {
  const startedAt = new Date(Date.now() - 10 * 60 * 1000)
    .toISOString()
    .replace(/\.\d{3}Z$/, "Z");
  const payload = {
    receiver: "agent-k-demo-console",
    status: "firing",
    alerts: [
      {
        status: "firing",
        labels: {
          alertname: "HighErrorRateSLOBurn",
          service: "agent-k-rag-service",
          severity: "critical",
        },
        annotations: {
          burn_rate: "2.4",
          demo_scenario: scenario,
        },
        startsAt: startedAt,
      },
    ],
  };

  const response = await fetch(`${baseUrl()}/alerts/webhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(
      `alert webhook rejected: ${response.status} ${await response.text().catch(() => "")}`,
    );
  }
}

export async function listInvestigations(signal?: AbortSignal): Promise<Investigation[]> {
  const response = await fetch(`${baseUrl()}/api/investigations`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`investigations unavailable: ${response.status}`);
  }
  return (await response.json()) as Investigation[];
}
