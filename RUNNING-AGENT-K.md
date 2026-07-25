# Running Agent K — Team Guide

This is the single "how do I run this thing" doc for teammates. It covers the
current state of the codebase (Phases 1-6 built, Phase 7 partially — the report
page is done, the dashboard/eval/blog are not) and how to bring up every piece
that exists today. For SigNoz-specific standup
detail/troubleshooting, see [SIGNOZ-RUNBOOK.md](SIGNOZ-RUNBOOK.md) — this doc
assumes that one for anything SigNoz-install-specific and focuses on the app
itself.

## 1. What's actually runnable right now

| Component | Status | Runs as |
|---|---|---|
| SigNoz observability backend | Built (Phase 1) | Docker, via Foundry |
| `rag-postgres` (Postgres 16 + pgvector) | Built (Phase 2) | Docker |
| RAG FastAPI app (`app/main.py`) — `/ask`, `/healthz`, `/admin/flags`, `/alerts/webhook` | Built (Phases 2-5) | `uvicorn`, local process |
| Agent K investigation loop (`app/investigation.py`) | Built (Phase 5), wired into the webhook | Same process as the app above — no separate process yet |
| Law 2 policy gate (`app/policy.py`) | Built (Phase 6) | In-process, runs at the end of each investigation |
| `deployer` sidecar (Law 2 rollback executor) | Built (Phase 6), **not yet live-verified** | Docker, `deployer` service |
| Incident report page (`/report`, `/report/{id}`) | Built (Phase 7) | Same FastAPI process |
| Hand-built SigNoz dashboard/alerts | **Not built** (Phase 3 wave 3 / Phase 7) | SigNoz UI |

There is no `docker-compose` that starts "the whole product" in one command —
SigNoz comes up via Foundry, Postgres comes up via `docker compose`, and the
FastAPI app runs locally with `uvicorn`. Follow the steps below in order.

## 2. Prerequisites (once per machine)

- Docker Desktop / Docker Engine + Compose v2, with memory raised to 6-8GB
  (see [SIGNOZ-RUNBOOK.md §0](SIGNOZ-RUNBOOK.md#0-precondition-docker-desktop-memory-d-03))
- Python 3.11 or 3.12
- `foundryctl` (SigNoz's deploy CLI): `curl -fsSL https://signoz.io/foundry.sh | bash`

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Note (2026-07-25): a fresh `pip install -r requirements.txt` pulls in
> `mcp==1.28.1` correctly. If you're reusing an older venv and see
> `ModuleNotFoundError: No module named 'mcp'` when running tests, just
> re-run the install above — the package is pinned in `requirements.txt`,
> it was only missing from one stale local venv.

## 3. Environment variables

Copy `.env.example` to `.env` and fill in real values. Everything the code
actually reads via `os.getenv`/`os.environ`:

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | `app/db.py`, Alembic | Defaults to `postgresql+asyncpg://agentk:agentk@localhost:5432/agentk` if unset — matches the `rag-postgres` container below |
| `LLM_PROVIDER` | `app/llm.py` | `groq` (default) / `cerebras` / `gemini` — this is the "one env var switches provider" knob |
| `GROQ_API_KEY` / `CEREBRAS_API_KEY` / `GEMINI_API_KEY` | `app/llm.py` | Only the one matching `LLM_PROVIDER` is required; client construction now fails fast (`MissingProviderKeyError`) instead of silently leaking an unrelated key |
| `EMBEDDING_MODEL` | `app/embeddings.py` | Defaults to `all-MiniLM-L6-v2` if unset |
| `ADMIN_TOKEN` | `app/flags.py` (`/admin/flags` POST) | If unset, the admin endpoint is unauthenticated (fine for local demo only) |
| `SIGNOZ_URL` | `app/signoz_mcp.py`, `app/claims.py` | Passed to the MCP server subprocess **and** used as the base for every evidence deep link. Defaults to `http://localhost:8080`, matching this deployment |
| `SIGNOZ_API_KEY` | `app/signoz_mcp.py` | Passed through to the SigNoz MCP server subprocess |
| `DEPLOYER_URL`, `DEPLOYER_TOKEN` | `app/rollback.py` | Where the deployer sidecar lives and the shared token authenticating `POST /rollback`. `DEPLOYER_TOKEN` must match the sidecar's own (see §6a) |
| `SIGNOZ_MCP_COMMAND` | `app/signoz_mcp.py` | Path/command to launch the SigNoz MCP server binary |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `app/telemetry.py` | Defaults to SigNoz's OTLP-HTTP ingest, `http://localhost:4318` |
| `OTEL_SERVICE_NAME` | `app/telemetry.py` | Service name shown in SigNoz |

## 4. Standing up SigNoz (once, or after a clean-machine rebuild)

```bash
foundryctl gauge -f casting.yaml
foundryctl forge -f casting.yaml -p ./pours
foundryctl cast -f casting.yaml
```

Then **do the first-run org registration** — SigNoz's OTLP receivers do not
bind until this runs once per fresh stack (this bit the team once already,
see [SIGNOZ-RUNBOOK.md §1.5](SIGNOZ-RUNBOOK.md#15-required-first-run-setup-do-this-immediately-after-cast-before-anything-else)):

```bash
curl -s -X POST http://localhost:8080/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","name":"Your Name","orgName":"agent-k","password":"<12+ chars, upper/lower/number/symbol>","orgId":"","isAnonymous":false}'
```

Verify: `docker ps` should show `signoz-signoz-0`, `signoz-ingester-1`,
clickhouse, keeper, and `signoz-metastore-postgres-0`, all healthy. SigNoz UI
at http://localhost:8080.

> As of this writing, this stack is **already running** in the dev
> environment (`docker ps` shows it up for 34h) — most teammates won't need
> to redo this unless testing the clean-machine-rebuild timing (TELE-02).

## 5. Standing up the RAG datastore

```bash
docker compose -f pours/deployment/compose.yaml up -d rag-postgres   # or however your compose service is named — check `docker ps`
alembic upgrade head          # applies the pgvector `documents` table migration
python -m scripts.seed_corpus # idempotent — embeds data/corpus/*.md locally via sentence-transformers, no network calls
```

`rag-postgres` is also already running in the current dev environment.

## 6. Running the RAG app + Agent K

Agent K's investigation loop is **not a separate service** — it lives inside
the same FastAPI process and is triggered by `POST /alerts/webhook`.

```bash
uvicorn app.main:app --reload --port 8000
```

Smoke-test:

```bash
curl http://localhost:8000/healthz
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'
```

A healthy `/ask` call emits `rag.retrieval`, `rag.prompt_construction`, and
`chat` spans (plus a free SQLAlchemy `SELECT` span underneath retrieval) —
visible in SigNoz's Traces Explorer within a widened time window (SigNoz
defaults to "last 30 minutes").

### Triggering an investigation manually (no real SigNoz alert needed yet)

```bash
curl -X POST http://localhost:8000/alerts/webhook -H "Content-Type: application/json" \
  -d '{"...": "see tests/test_webhook.py for the exact payload shape this endpoint expects"}'
```

This starts a background investigation (`app/investigation.py`) that queries
SigNoz via the MCP wrapper, forms an LLM hypothesis, and reaches a terminal
`REPORTED`/`ESCALATED` state. Open **http://localhost:8000/report** to read the
result (see §6b), or watch the `agentk.investigation` / `agentk.hypothesis`
spans in SigNoz.

### Toggling failure scenarios (Phase 3)

```bash
curl -X POST http://localhost:8000/admin/flags -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{"name": "prompt_regression", "enabled": true}'
curl http://localhost:8000/admin/flags   # read current state, no auth required
```

Flag names: `prompt_regression`, `retry_storm`, `retrieval_latency`,
`db_pool_exhaustion` (check `app/flags.py` for the authoritative list).

## 6a. The deployer sidecar (Law 2)

The sidecar is the **only** component that gets the Docker socket. Agent K never
holds it — Agent K's entire ability to change anything is one authenticated
`POST /rollback` with an empty body.

```bash
export DEPLOYER_TOKEN="$(openssl rand -hex 24)"   # required; the sidecar 503s without it
docker compose up -d --build deployer
curl http://localhost:9000/healthz
```

Add the same `DEPLOYER_TOKEN` to your `.env` so the app-side caller
(`app/rollback.py`) sends a matching token.

Where a rollback comes from: an investigation that reaches a terminal REPORTED
state runs `evaluate_policy()`. Only if **all six** checks pass (SLO breach,
allowlist, cooldown, confidence ≥ 0.70, deployment-class cause, sandbox scope)
does Agent K call the sidecar. Everything else produces a denial with an
evidence-linked recommendation and no action. By design, `prompt_regression` and
`retry_storm` can approve; `retrieval_latency` and `db_pool_exhaustion` always deny.

### Phase 6 human verification (HV-3) — not yet done

The sidecar's contract is fully unit-tested with the Docker layer faked, but **no
real rollback has ever run**, because the app isn't containerized. To close it:

1. Write a `Dockerfile` for the RAG app and add a `rag-app` service to
   `docker-compose.yaml` using `image: agent-k-rag:${RAG_IMAGE_TAG:-v1-good}`.
2. Build two tags from the same source — `v1-good`, and `v2-broken` with the
   `prompt_regression` flag default baked ON. You do **not** need a second codebase.
3. Bring up `rag-app` on `v2-broken`, fire an alert at `/alerts/webhook` with a
   `burn_rate` annotation > 1.0 and `service: agent-k-rag-service`, and confirm
   the sidecar recreates it on `v1-good`.
4. Confirm the `deployment.marker` span and the `agentk.policy.decision` /
   `agentk.action.rollback` spans render in SigNoz.

## 6b. Reading the incident report (Phase 7)

Once the app is running, the report pages are served from the same process:

- **http://localhost:8000/report** — every past investigation, newest first, with a
  count strip (rollbacks / denied / needs-human).
- **http://localhost:8000/report/{id}** — one incident's full RCA: claims with
  recalibrated confidence, evidence table with clickable SigNoz links, all six
  policy checks with pass/fail, the action outcome, and Agent K's own
  token/query/duration numbers.

Three things the page deliberately does, worth knowing before you read it:

- A **denied** verdict is shown as a normal, correct outcome — not an error. Agent K
  declining to act is the safety gate working.
- A rollback that executed but whose recovery could **not** be verified in SigNoz is
  never shown as a success. It says so explicitly.
- A loop-breaker/cost-watchdog investigation renders as **needs human** with no
  verdict — it never reached the act stage, so there is nothing to report.

> **Evidence links point at `SIGNOZ_URL`**, which now defaults to
> `http://localhost:8080` — correct for this deployment. Override it only if your
> SigNoz is elsewhere; a wrong value makes every "Open in SigNoz" link on the
> report page 404.

To see the pages without standing up the whole live chain (no DB, no API key, no
server needed):

```bash
python -m scripts.seed_demo_report
```

That renders `build/report-preview/*.html` from **synthetic** investigations. It is a
development aid only — never use its output as a screenshot in the demo video, blog,
or eval results.

## 7. Running tests

```bash
pytest -q
```

Currently: **188 passed, 1 skipped** (the skipped test needs a live DB
connection and is excluded by default — see `tests/test_integration_rag.py`).

## 8. Current gaps / what NOT to assume works yet

- **No rollback has ever actually executed.** The policy gate and sidecar are
  built and tested, but the app isn't containerized — see HV-3 in §6a above.
- **The full live chain has never run once.** Every phase from 2 through 7 is
  offline-tested with the live half mocked. No investigation has ever gone
  alert → MCP evidence → LLM hypothesis → policy verdict for real, because no
  `signoz-mcp-server` binary is installed and the MCP tool names in
  `app/investigation.py`'s `EVIDENCE_QUERY_PLAN` are still guesses. This is the
  single biggest risk left — everything else is downstream of it.
- **The report page renders, but its evidence links are dead by default** —
  `SIGNOZ_URL` must be set to `http://localhost:8080` (see §3).
- **No eval harness and no finished dashboard** — EVAL-01..04 and DASH-03/04
  have zero code, and the SUB-01 AI-usage disclosure is unwritten
  (that one is a disqualification risk and takes five minutes).
- Several Phase 2-5 requirements are marked "code complete, needs human
  verification" in `.planning/REQUIREMENTS.md` — the code and offline tests
  are done, but nobody has yet: (a) run `/ask` against a real Groq/Cerebras/
  Gemini key, or (b) confirmed spans/evidence links actually render in the
  live SigNoz UI. Since the SigNoz stack and Postgres are already running in
  this dev environment, either of these can likely be closed out quickly by
  whoever picks this up next — it mostly needs a real `GROQ_API_KEY` in
  `.env` and 10 minutes clicking through the SigNoz UI.
- The `landing/` directory is a separate Next.js marketing site (for the
  hackathon's warm-up blog / landing page), unrelated to Agent K's core
  submission requirements — don't confuse it with the actual product.

## 9. Where to look next

- Full requirement-by-requirement status: [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md)
- Phase-by-phase plan and what's left: [.planning/ROADMAP.md](.planning/ROADMAP.md)
- Session state / handoff notes: [.planning/STATE.md](.planning/STATE.md)
- SigNoz install/troubleshooting detail: [SIGNOZ-RUNBOOK.md](SIGNOZ-RUNBOOK.md)
