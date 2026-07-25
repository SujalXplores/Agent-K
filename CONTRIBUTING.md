# Contributing to Agent K

Thanks for your interest in Agent K. This guide covers how to set up the
project, run tests, and submit changes.

## Project layout

| Path | What it is |
| --- | --- |
| `app/` | FastAPI RAG support service (the monitored app) |
| `data/corpus/` | 72 synthetic support docs |
| `alembic/` | DB migrations |
| `scripts/` | Seed, probe, and timing scripts |
| `tests/` | Offline unit plus live database integration tests |
| `landing/` | Static Next.js marketing site (separate app) |

## Prerequisites

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.11 or 3.12 | Avoid 3.13, some OTel contrib packages lag |
| Docker | Desktop or Engine plus Compose v2 | 6 to 8 GB memory for SigNoz |
| Node.js | 22 | Only needed for the `landing/` app |

## Set up the RAG service

The canonical setup uses `make bootstrap` (one command: venv, install, .env
copy). The underlying steps are documented here for reference.

```bash
git clone https://github.com/SujalXplores/Agent-K.git
cd Agent-K

# Option A: make (recommended)
make bootstrap

# Option B: manual
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"                                # editable install + ruff/pytest

cp .env.example .env
# fill in GROQ_API_KEY (and or CEREBRAS_API_KEY / GEMINI_API_KEY)
# generate DEPLOYER_TOKEN: python -c "import secrets; print(secrets.token_hex(24))"
```

`pip install -e ".[dev]"` installs the `app` and `deployer` packages in
editable mode plus dev tooling (ruff, pytest, pytest-cov). This is what lets
scripts in `scripts/` import `app.*` without a `sys.path` shim.

## Stand up SigNoz and the datastore

```bash
# SigNoz via Foundry
foundryctl cast -f casting.yaml

# rag postgres (pgvector)
docker compose up -d
```

See [`SIGNOZ-RUNBOOK.md`](SIGNOZ-RUNBOOK.md) for the full SigNoz standup
guide, including the required first run org and register step.

## Run migrations and seed the corpus

```bash
make migrate     # alembic upgrade head
make seed       # python -m scripts.seed_corpus (idempotent)
```

## Run the service

```bash
make dev        # uvicorn app.main:app --reload --port 8000
```

Smoke test:

```bash
make smoke      # hits /healthz and one /ask
```

## Run tests

| Command | What it does |
| --- | --- |
| `make test` | Offline unit tests (mocked, no DB, no network) |
| `make test-integration` | Live database tests (requires rag postgres) |
| `make coverage` | Tests with HTML coverage report (opens htmlcov/) |
| `make probe` | Measure the real /ask span set into out.json |

## Demo reset

```bash
make reset      # POST /admin/reset - clears flags, alerts, investigations, cooldowns
```

Clears every in-process store so a demo can re-run without restarting uvicorn.
Does not touch SigNoz, Postgres, or the deployer.

## Running the full demo

```bash
make demo-up    # bring up the full backend (cross-platform: works on Windows + Unix)
make demo-ui    # start the demo Next.js UI (Flowdeck support + Agent K console)
# or: make demo  # one command: backend then UI
```

See [`DEMO.md`](DEMO.md) for the full walkthrough of the four incidents.

## Set up the landing page (optional)

```bash
cd landing
npm install
npm run dev
```

See [`landing/README.md`](landing/README.md) for the full landing page guide.

## Code style

| Tool | Purpose |
| --- | --- |
| `ruff` | Lint and format (config in `pyproject.toml`) |
| `pytest` plus `pytest-asyncio` | Tests (config in `pyproject.toml`) |

| Command | What it does |
| --- | --- |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` (writes changes) |
| `make check` | Lint + tests (pre-PR gate) |
| `make check-env` | Validate .env (DEPLOYER_TOKEN, provider key, DB/SigNoz) |
| `make pre-commit-install` | Install git pre-commit hooks (ruff + format + check-env) |

Key conventions:

- No em dashes in user facing copy. Use a colon, comma, or period instead.
- Every claim in docs and reports must be evidence backed.
- Every action must pass the Law 2 policy gate in code.
- Every LLM call must record self telemetry (Law 3).
- Never log raw prompt, completion, or API key text as a span attribute.
- One OpenAI compatible client module, provider switched via env var only.
- One datastore (PostgreSQL plus pgvector), no separate vector DB.

## Pull request checklist

- [ ] `make check` passes (lint + tests)
- [ ] Integration tests pass (if DB changes): `make test-integration`
- [ ] No raw prompt, completion, or API key text in span attributes
- [ ] Every new claim in docs carries a resolvable evidence link
- [ ] Every new action passes through the Law 2 policy gate
- [ ] Every new LLM call records self telemetry
- [ ] No em dashes in user facing copy
- [ ] `casting.yaml` and `casting.yaml.lock` stay committed and in sync

## AI assistance disclosure

This project uses AI coding assistance (Claude Code, GitHub Copilot),
disclosed per the hackathon rules. All AI assisted work must be reviewed by
a human before merge. Do not hide AI assistance in commit messages or PRs.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License. See [`LICENSE`](LICENSE).
