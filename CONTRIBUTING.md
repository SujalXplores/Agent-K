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

```bash
git clone https://github.com/SujalXplores/Agent-K.git
cd Agent-K

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in GROQ_API_KEY (and or CEREBRAS_API_KEY / GEMINI_API_KEY)
```

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
alembic upgrade head
python -m scripts.seed_corpus
```

## Run the service

```bash
uvicorn app.main:app --reload
```

## Run tests

| Command | What it does |
| --- | --- |
| `pytest` | Offline unit tests (mocked, no DB, no network) |
| `pytest -m integration` | Live database tests (requires rag postgres) |
| `python scripts/probe_ask_spans.py out.json` | Measure the real /ask span set |

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
| `ruff` | Lint and format |
| `pytest` plus `pytest-asyncio` | Tests |

Key conventions:

- No em dashes in user facing copy. Use a colon, comma, or period instead.
- Every claim in docs and reports must be evidence backed.
- Every action must pass the Law 2 policy gate in code.
- Every LLM call must record self telemetry (Law 3).
- Never log raw prompt, completion, or API key text as a span attribute.
- One OpenAI compatible client module, provider switched via env var only.
- One datastore (PostgreSQL plus pgvector), no separate vector DB.

## Pull request checklist

- [ ] Tests pass: `pytest`
- [ ] Integration tests pass (if DB changes): `pytest -m integration`
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
