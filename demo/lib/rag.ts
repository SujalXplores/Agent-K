/**
 * Server-side client for the monitored RAG service.
 *
 * Everything in this module runs on the Next.js server, never in the browser.
 * That is deliberate: the FastAPI service has no CORS middleware and we are not
 * adding any, because that service is the judged artefact and its request path
 * is what every OTel span, GenAI attribute and failure-injection flag is
 * measured against. Proxying server-side leaves it untouched.
 *
 * The LLM call itself stays inside FastAPI. This app never talks to a model
 * provider — if it did, the generation would happen outside the instrumented
 * code path and the telemetry that the whole project rests on would be blind
 * to it.
 */

/** A retrieved corpus document surfaced alongside an answer (app/schemas.py Source). */
export type RagSource = {
  doc_id: string;
  title: string;
};

/** POST /ask response body (app/schemas.py AskResponse). */
export type AskResponse = {
  answer: string;
  sources: RagSource[];
};

/** GET/POST /admin/flags response body (app/schemas.py FlagStateResponse). */
export type FlagState = {
  flags: Record<string, boolean>;
};

export class RagServiceError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "RagServiceError";
    this.status = status;
  }
}

/**
 * Base URL of the monitored RAG service. Local docker-compose exposes it on
 * :8000; for a hosted demo this points at whatever tunnel or host fronts it.
 */
function baseUrl(): string {
  return (process.env.RAG_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

/**
 * Ask the RAG service a question.
 *
 * No retry, no timeout race, no fallback answer. Under the retry-storm and
 * db-pool-exhaustion scenarios this call is *supposed* to be slow or to fail —
 * papering over that here would hide the very symptom the demo exists to show,
 * and would also mean the customer-visible experience no longer matches what
 * SigNoz recorded.
 */
export async function ask(question: string, signal?: AbortSignal): Promise<AskResponse> {
  const response = await fetch(`${baseUrl()}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new RagServiceError(detail || `RAG service returned ${response.status}`, response.status);
  }

  return (await response.json()) as AskResponse;
}

/** Read which failure scenarios are currently switched on. */
export async function readFlags(signal?: AbortSignal): Promise<FlagState> {
  const response = await fetch(`${baseUrl()}/admin/flags`, {
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new RagServiceError(`RAG service returned ${response.status}`, response.status);
  }

  return (await response.json()) as FlagState;
}
