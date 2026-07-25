# Agent K - developer task runner.
#
# Every target below is the canonical entry point for the thing it does. If you
# find yourself typing a longer command in the README or CONTRIBUTING.md, add a
# target here instead and point the docs at `make <target>`.
#
# Run `make` (or `make help`) with no arguments to list every target with its
# description. Targets are grouped by workflow: setup, run, test, demo, quality.
#
# Cross-platform note: this Makefile uses plain `python` and standard tools. On
# Windows, `make` is available via `winget install GnuWin32.Make` or via the
# Git for Windows bash. For a no-make fallback, every target's underlying
# command is documented in CONTRIBUTING.md.

.PHONY: help bootstrap install dev test test-integration test-fast coverage seed migrate \
        smoke reset eval eval-full probe demo-report seed-demo-report \
        demo demo-up demo-ui up down ps \
        lint format format-check format-all check check-env \
        dashboard dashboard-create log-foundry \
        pre-commit-install pre-commit-run

# --- Defaults ----------------------------------------------------------------
# PYTHON is the interpreter used for all `python -m ...` invocations. Override
# with `make PYTHON=python3.12 ...` if your machine's default `python` is the
# wrong version.
PYTHON ?= python
# VENV is the virtualenv directory. Override with `make VENV=.venv-312 ...`.
VENV ?= .venv
# APP_URL is the running RAG service base URL for smoke/reset/eval targets.
APP_URL ?= http://localhost:8000

# --- Setup -------------------------------------------------------------------

bootstrap: ## Full fresh-machine setup: create venv, install deps, copy .env
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip || $(VENV)/Scripts/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]" || $(VENV)/Scripts/pip install -e ".[dev]"
	@if [ ! -f .env ]; then cp .env.example .env; \
	  echo ""; echo "  Created .env from .env.example. Fill in:"; \
	  echo "    GROQ_API_KEY     - your LLM provider key (or CEREBRAS/GEMINI)"; \
	  echo "    DEPLOYER_TOKEN   - generate with: python -c \"import secrets; print(secrets.token_hex(24))\""; \
	  echo ""; \
	else echo "  .env already exists, leaving it untouched."; fi
	@echo ""
	@echo "  Next: make dev   (starts the RAG service on :8000)"
	@echo "        make test  (offline unit tests, no DB/key needed)"

install: ## Install the package + dev deps into the current environment (no venv)
	pip install -e ".[dev]"

check-env: ## Validate .env: DEPLOYER_TOKEN, provider key, DB/SigNoz reachability
	$(PYTHON) scripts/check_env.py

# --- Run ---------------------------------------------------------------------

dev: ## Start the RAG service with --reload on port 8000
	$(PYTHON) -m uvicorn app.main:app --reload --port 8000

deployer: ## Start the Law 2 deployer sidecar on port 9000
	$(PYTHON) -m uvicorn deployer.main:app --port 9000

# --- Test --------------------------------------------------------------------

test: ## Run offline unit tests (mocked, no DB, no network, no API key)
	$(PYTHON) -m pytest

test-integration: ## Run live-database integration tests (requires rag-postgres)
	$(PYTHON) -m pytest -m integration

test-fast: ## Run tests stopping at the first failure
	$(PYTHON) -m pytest -x

coverage: ## Run tests with coverage report (opens htmlcov/index.html)
	$(PYTHON) -m pytest --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "  Coverage report: htmlcov/index.html"

# --- Data --------------------------------------------------------------------

seed: ## Embed and upsert the 72-doc corpus into rag-postgres (idempotent)
	$(PYTHON) -m scripts.seed_corpus

migrate: ## Apply Alembic migrations to the configured DATABASE_URL
	$(PYTHON) -m alembic upgrade head

# --- Demo / eval -------------------------------------------------------------

smoke: ## Hit /healthz and one /ask against a running APP_URL (default :8000)
	@echo "  -> healthz"
	@curl -fsS $(APP_URL)/healthz || { echo "  FAIL: $(APP_URL) not reachable. Start with: make dev"; exit 1; }
	@echo ""
	@echo "  -> /ask"
	@curl -fsS -X POST $(APP_URL)/ask -H "Content-Type: application/json" \
	  -d '{"question":"How do I rotate my API key?"}' || { echo "  FAIL: /ask failed. Check GROQ_API_KEY and DATABASE_URL."; exit 1; }
	@echo ""
	@echo "  OK: service is up and answering."

reset: ## Clear in-process flags/alerts/investigations/cooldowns (no restart)
	@ADMIN_TOKEN="$${ADMIN_TOKEN:-}"; \
	curl -fsS -X POST $(APP_URL)/admin/reset \
	  $${ADMIN_TOKEN:+-H "X-Admin-Token: $$ADMIN_TOKEN"} \
	  || { echo "  FAIL: $(APP_URL) not reachable. Start with: make dev"; exit 1; }
	@echo "  OK: demo state cleared."

eval: ## Run the 4-incident eval harness (needs app on :8000 + SigNoz + provider key)
	$(PYTHON) -m scripts.run_eval --runs 1

eval-full: ## Run the full 12-run eval (4 incidents x 3 runs)
	$(PYTHON) -m scripts.run_eval

probe: ## Measure the real /ask span set into out.json (fresh process)
	$(PYTHON) -m scripts.probe_ask_spans out.json

demo-report: ## Seed three SYNTHETIC investigations so /report renders without a live stack
	$(PYTHON) -m scripts.seed_demo_report
	@echo "  Open: $(APP_URL)/report"
	@echo "  NOTE: data is fabricated - see scripts/seed_demo_report.py header."

seed-demo-report: ## Alias for demo-report (seed synthetic investigations)
	$(PYTHON) -m scripts.seed_demo_report
	@echo "  Open: $(APP_URL)/report"

dashboard: ## Build the Agent K SigNoz dashboard JSON (use --create to push to SigNoz)
	$(PYTHON) -m scripts.build_dashboard

dashboard-create: ## Build the dashboard AND create it in SigNoz via MCP
	$(PYTHON) -m scripts.build_dashboard --create

# --- Demo orchestration ------------------------------------------------------

demo-up: ## Bring up the full backend (SigNoz + Postgres + rag-app) - cross-platform
	$(PYTHON) scripts/demo_up.py

demo-ui: ## Start the demo Next.js UI (Flowdeck support + Agent K console)
	cd demo && npm install && npm run dev

demo: ## One-command demo: bring up backend, then start the UI
	$(PYTHON) scripts/demo_up.py
	@echo ""
	@echo "  Backend is up. Starting the demo UI..."
	cd demo && npm install && npm run dev

log-foundry: ## Time `foundryctl cast` and append a row to TELEMETRY-REBUILD-LOG.md
	bash scripts/time-foundry-cast.sh

# --- Docker full-stack (stretch) -------------------------------------------

up: ## Start all docker-compose services (rag-postgres + rag-app + deployer)
	docker compose up -d

down: ## Stop all docker-compose services
	docker compose down

ps: ## Show running docker-compose services and their health
	docker compose ps

# --- Quality -----------------------------------------------------------------

lint: ## Run ruff lint check
	$(PYTHON) -m ruff check .

format: ## Run ruff format (writes changes)
	$(PYTHON) -m ruff format .

format-check: ## Run ruff format check (no writes, for CI/pre-commit)
	$(PYTHON) -m ruff format --check .

format-all: ## One-shot: format the entire codebase (run once to adopt ruff format)
	$(PYTHON) -m ruff format .
	@echo "  Done. Review the diff and commit - this is a one-time formatting pass."

check: lint test ## Pre-PR gate: lint + tests (format-check is separate until the codebase is fully formatted)
	@echo ""
	@echo "  OK: lint clean, tests pass."

pre-commit-install: ## Install git pre-commit hooks (ruff + format + check-env)
	pip install pre-commit
	pre-commit install
	@echo "  Pre-commit hooks installed. Run 'pre-commit run --all-files' to check."

pre-commit-run: ## Run all pre-commit hooks on all files
	pre-commit run --all-files

# --- Help --------------------------------------------------------------------

help: ## Show this help
	@echo "Agent K - developer tasks"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "  %-20s %s\n", "TARGET", "DESCRIPTION"; printf "  %-20s %s\n", "------", "-----------"} \
	  /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "Override defaults: make PYTHON=python3.12 VENV=.venv-312 APP_URL=http://localhost:9000 test"

# Default target - `make` with no args shows help.
.DEFAULT_GOAL := help
