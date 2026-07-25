# Flowdeck Support — Agent K demo app

The customer-facing surface of the demo. **Flowdeck** is the fictional B2B SaaS
product that the monitored RAG service's corpus (`../data/corpus/`, 72
hand-authored support docs) is written about; this app is Flowdeck's help centre.

It exists so the demo has a real product to break. When a seeded failure
scenario is switched on, the damage shows up here as a customer would
experience it — answers losing their citations, replies crawling, requests
failing — and _then_ the story moves to SigNoz, the alert, and Agent K.

## Provenance

Cloned and owned from [**assistant-ui**](https://github.com/assistant-ui/assistant-ui)
(MIT), scaffolded via `npx assistant-ui@latest create -t minimal`. The chat
components under `components/assistant-ui/` are vendored source, not a runtime
dependency on a template — they are ours to edit, and they have been edited
(source citations, Flowdeck welcome copy).

Removed from the upstream scaffold: `@ai-sdk/openai`, `ai`, and
`@assistant-ui/react-ai-sdk`, plus the `app/api/chat` route they served.

## Architecture

```
browser ──▶ /api/ask (Next.js server route) ──▶ FastAPI POST /ask ──▶ pgvector + LLM
```

Two rules shape this:

1. **The LLM call stays inside FastAPI.** Every `gen_ai.*` span, every failure
   flag, and the whole judged telemetry story lives on that code path. A chat UI
   that called a model itself — the upstream template's default — would generate
   answers outside the instrumented path and make the telemetry blind to them.
2. **The browser never talks to FastAPI.** That service has no CORS middleware
   and isn't getting any: it's the judged artefact, and its request path is what
   the eval runs measured. Proxying server-side leaves it untouched.

So this app holds no model API key, and `POST /ask` is called exactly as the
eval harness calls it.

| Path                                     | What it is                                             |
| ---------------------------------------- | ------------------------------------------------------ |
| `lib/rag.ts`                             | Server-only client for `/ask` and `/admin/flags`       |
| `lib/rag-adapter.ts`                     | assistant-ui `ChatModelAdapter` over `/api/ask`        |
| `lib/flowdeck.ts`                        | Brand constants, starter questions, the four scenarios |
| `app/api/ask/route.ts`                   | Server proxy to `POST /ask`                            |
| `app/api/flags/route.ts`                 | Read-only proxy to `GET /admin/flags`                  |
| `components/flowdeck/incident-strip.tsx` | Shows which scenario is live                           |
| `components/assistant-ui/`               | Vendored, edited assistant-ui components               |

## Run it

The RAG service must be up first — see [`../RUNNING-AGENT-K.md`](../RUNNING-AGENT-K.md).

```bash
cp .env.example .env.local   # set RAG_API_URL
npm install
npm run dev                  # http://localhost:3000
```

Verify:

```bash
curl -X POST localhost:3000/api/ask -H "Content-Type: application/json" -d '{"question":"How do I rotate an API key?"}'
```

## Notes

- **The incident strip is for the demo audience, not Flowdeck's fictional
  customers.** It makes the injected fault legible on screen so a viewer can
  connect the degraded answer to the scenario to the telemetry without
  narration. It is hidden when nothing is wrong.
- **`/api/flags` is read-only.** It cannot toggle a scenario — that's the demo
  operator's deliberate action against `/admin/flags` with the admin token.
- **No retries or fallback answers in the request path.** Under the retry-storm
  and db-pool-exhaustion scenarios this call is _supposed_ to be slow or to
  fail; smoothing that over would hide the symptom and make the customer
  experience stop matching what SigNoz recorded.
- **Only the newest question is sent.** `POST /ask` is a single-turn stateless
  contract, so there is no history to forward.
