# Agent K — Monitored RAG Support Service

The "patient" half of Agent K: a FastAPI + PostgreSQL/pgvector RAG support-answering
service that is fully OpenTelemetry-instrumented and deliberately breakable on cue
via four feature-flag-toggled failure scenarios.

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker Desktop** (for PostgreSQL + pgvector)
- **Groq API key** (free tier — get one at [console.groq.com](https://console.groq.com))

### Setup

```bash
# 1. Install dependencies
cd apps/rag-service
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your-key-here

# 3. Start PostgreSQL with pgvector
docker compose up -d postgres

# 4. Generate the synthetic corpus (50 support docs)
python -m corpus.generate

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

The server auto-seeds the corpus on startup. If the database isn't ready when the
server starts, run `python -m corpus.generate` after the DB is up, then hit
`POST /admin/seed` to re-seed.

### Verify it's running

```bash
curl http://localhost:8000/health
```

## Using the Service

### Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'
```

### Trigger a failure scenario

```bash
# Enable prompt regression (Incident 1)
curl -X POST http://localhost:8000/admin/flags/prompt_regression \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Ask again — the answer will be broken
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I reset my password?"}'

# Disable the flag
curl -X POST http://localhost:8000/admin/flags/prompt_regression \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Record a deployment marker

```bash
curl -X POST http://localhost:8000/admin/deploy \
  -H "Content-Type: application/json" \
  -d '{"version": "v2", "note": "updated prompt template"}'

curl http://localhost:8000/admin/deploy
```

## The Four Failure Scenarios

| # | Flag | What happens | Deployment-caused? | Expected rollback verdict |
|---|------|-------------|-------------------|--------------------------|
| 1 | `prompt_regression` | Broken prompt template → garbage answers | Yes | ALLOW |
| 2 | `retry_storm` | Low timeout + retries → cost spike | Yes | ALLOW |
| 3 | `retrieval_latency` | Artificial delay → slow retrieval | No | DENY |
| 4 | `pool_exhaustion` | Pool size=1 → connection errors | No | DENY |

**Important:** Toggling a flag does NOT auto-create a deployment marker. Markers
are created separately via `/admin/deploy`. This preserves the distinction Agent K's
policy gate depends on (Incidents 1/2 are deployment-caused; 3/4 are not).

## Telemetry

By default, telemetry is printed to the console (`OTEL_EXPORTER=console`). To send
telemetry to SigNoz, set `OTEL_EXPORTER=otlp` and `OTEL_EXPORTER_OTLP_ENDPOINT` to
your SigNoz collector URL.

Spans emitted:
- `rag.ask` — the full request (parent span)
- `rag.retrieval` — the pgvector search step
- `rag.generation.llm_call` — the LLM call (with `gen_ai.*` attributes)
- `deployment.marker` — deployment marker creation
- Auto-instrumented: FastAPI HTTP spans, SQLAlchemy DB query spans

## Running Tests

```bash
cd apps/rag-service
pytest tests/ -v
```

Tests cover:
- Feature flag toggle logic
- All four failure mode configs (on/off/custom params)
- GenAI span attribute helper
- Deployment marker CRUD
- OTel initialization

## Smoke Test

```bash
# Start the server first, then:
python scripts/smoke_test.py
```

This script exercises all four failure scenarios end-to-end: baseline → failure
mode → recovery, plus deployment marker creation.

## Switching LLM Providers

Set `LLM_PROVIDER` in `.env`:
- `groq` (default) — `llama-3.1-8b-instant`
- `cerebras` — `llama-3.1-8b-instant`
- `gemini` — `gemini-2.0-flash`

Each provider has its own `*_API_KEY`, `*_BASE_URL`, and `*_MODEL` env vars. The
single OpenAI-compatible client swaps `base_url` based on the provider — no code
changes needed.

## Project Structure

```
apps/rag-service/
├── app/
│   ├── main.py              # FastAPI app, /ask endpoint, OTel wiring
│   ├── config.py            # Settings from env vars
│   ├── db.py                # SQLAlchemy async engine + pgvector
│   ├── retrieval.py         # Document model, corpus seeding, vector search
│   ├── llm_client.py        # OpenAI-compatible LLM client
│   ├── otel.py              # OTel bootstrap + genai_span_attrs helper
│   ├── flags.py             # FeatureFlagStore + /admin/flags routes
│   ├── deploy.py            # Deployment marker store + /admin/deploy
│   └── failure_modes/
│       ├── prompt_regression.py
│       ├── retry_storm.py
│       ├── retrieval_latency.py
│       └── pool_exhaustion.py
├── corpus/
│   ├── generate.py          # Generates 50 synthetic support docs
│   └── docs/                # Generated .md files (created by generate.py)
├── tests/
│   ├── test_flags.py
│   ├── test_failure_modes.py
│   ├── test_otel.py
│   └── test_deploy.py
├── scripts/
│   └── smoke_test.py        # End-to-end smoke test
├── docker-compose.yml       # PostgreSQL + pgvector
├── requirements.txt
├── pyproject.toml           # pytest + ruff config
└── .env.example
```
