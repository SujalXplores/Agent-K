# Demoing Agent K

Two surfaces, one backend:

| | |
| --- | --- |
| `http://localhost:3000` | **Flowdeck Support** — the help centre. What a customer sees. |
| `http://localhost:3000/console` | **Agent K console** — run the four incidents, watch the three Laws. |
| `http://localhost:8000/report` | Full RCA reports with evidence links. |

## Start it

```bash
./scripts/demo_up.sh
```

Idempotent — safe to re-run; skips the image build and corpus seed once done.
Then, in a second terminal:

```bash
cd demo && npm install && npm run dev
```

You need two things in the repo-root `.env` that the script cannot supply:

- **`DEPLOYER_TOKEN`** — `docker-compose.yaml` interpolates `${DEPLOYER_TOKEN:?}`,
  so Compose refuses to start *any* service without it, `rag-postgres` included.
  Generate with `python -c "import secrets; print(secrets.token_hex(24))"`.
- **`GROQ_API_KEY`** (or Cerebras/Gemini). Without a provider key, retrieval works
  and investigations still run to a terminal state, but no answer is generated and
  no hypothesis is formed — every investigation escalates with zero claims. The
  demo is not watchable without it.

## What is real and what is a fixture

**Read this before demoing.** Do not present fixture output as live telemetry.

Real, on the real code path:

- Retrieval against pgvector over 72 locally-embedded support docs.
- All three GenAI-instrumented spans per `/ask`, plus the free SQLAlchemy DB span.
- The four failure scenarios and their deployment markers.
- The investigation state machine, Law 1's evidence stripping, Law 2's six-check
  zero-LLM gate, Law 3's self-telemetry, and both guardrails.
- The rollback, executed by the privilege-isolated `deployer` sidecar.

The fixture, when `SIGNOZ_MCP_COMMAND` points at `scripts/demo_mcp_server.py`:

- Evidence payloads are hand-authored, not queried from SigNoz. Every payload
  carries `"_source": "agent-k demo fixture (NOT live SigNoz)"`.
- **Evidence links do not resolve.** Law 1's "every link resolves" claim can only
  be demonstrated against a real instance, via `scripts/check_evidence_links.py`.

The fixture is never the default: `docker-compose.yaml` passes
`SIGNOZ_MCP_COMMAND` through empty, so an unconfigured stack falls back to the
real `signoz-mcp-server` binary and fails loudly rather than quietly serving
invented evidence. It also reads live flag state from `/admin/flags`, so toggling
a scenario genuinely changes what Agent K sees — there is no path by which it can
be told what to conclude.

To go live: blank `SIGNOZ_MCP_COMMAND`/`SIGNOZ_MCP_ARGS`, set
`SIGNOZ_URL`/`SIGNOZ_API_KEY`, and put the real binary on the path. No code
changes. See [`HOSTED-DEMO.md`](HOSTED-DEMO.md).

## The walkthrough

**1. Healthy.** Open the help centre. Ask "How do I rotate an API key?" — a
grounded answer, with the retrieved articles cited underneath. That citation row
is the customer-visible face of grounding; watch what happens to it next.

**2. Break it.** Console → **Prompt regression** → *Run this incident*. This sets
the flag, puts real traffic through `/ask`, and fires the alert webhook — the
same sequence `scripts/run_eval.py` runs.

**3. Customer view.** Back to the help centre. An amber strip names the live
scenario and says a rollback is eligible. Ask the same question: the answer has
lost its grounding.

**4. Agent K.** Back to the console. The panel fills in as the investigation
progresses: claims with their code-recalibrated confidence (Law 1), then the
verdict with all six checks (Law 2), then tokens/duration/MCP counts (Law 3).

**5. The gate approves**, the `deployer` sidecar re-creates `rag-app` from the
known-good tag, and Agent K re-queries to confirm recovery. *Recovery verified*
appears in the panel.

**6. The denial — the most important one.** Run **Retrieval latency**. The card
says *expect denied* and the gate denies it: there is no deployment marker, so
`deployment_related` fails. A rollback could not fix an infrastructure fault, and
the gate refuses to try. **This is the point of the whole project** — the model
does not get a vote, and the denial is visible proof that code is deciding.

**7. Guardrails.** Tighten a threshold and run any incident:

```bash
AGENT_K_TOKEN_BUDGET=1 docker compose up -d --force-recreate rag-app
```

The cost watchdog fires for real, on the same code path — the threshold moved,
the guardrail did not. `Guardrail fired` appears in the panel and the
investigation is marked needs-human. Same for
`AGENT_K_LOOP_BREAKER_THRESHOLD=0`. Unset them afterwards.

**8. The report.** *Full RCA report* → claims, evidence, the policy verdict, and
the verification result, addressable by incident id.

## Honest notes for the judges

- **Diagnosis accuracy is modest.** The recorded 12-run evaluation
  ([`evals/SUMMARY.md`](evals/SUMMARY.md)) got 5/12 diagnoses right, 3/9 on
  uncontaminated runs, while landing 10/12 expected verdicts. Say so. The
  interesting claim is not "the model is always right" — it is that a wrong
  diagnosis still cannot produce an unevidenced claim or an ungated action.
- **A denied verdict is a success**, not a failure to demo around.
- **The rollback needs the Docker socket**, held by the `deployer` sidecar as a
  structural isolation boundary. No free PaaS grants one, so Law 2 executes for
  real only on a machine you control — see `HOSTED-DEMO.md`.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| "Could not reach Flowdeck Support" | `rag-app` is down, or `RAG_API_URL` is wrong in `demo/.env.local`. |
| Compose aborts before starting anything | `DEPLOYER_TOKEN` empty in `.env`. |
| `/ask` 500s, investigations have 0 claims | No LLM provider key. |
| Port 5432 already allocated | Another Postgres holds it. Remap the host port in a gitignored `docker-compose.override.yaml` — needs `ports: !override`, since Compose *appends* list fields rather than replacing them. |
| Console scenario returns 422 | The alert envelope needs top-level `receiver` and `status`, not just `alerts`. |
| `docker compose up -d rag-app` tries to pull | `rag-app` has no `build:` stanza; build the image first (`demo_up.sh` does). |
