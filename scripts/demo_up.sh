#!/usr/bin/env bash
# Bring the whole demo up from a cold machine, in one command.
#
#   ./scripts/demo_up.sh
#
# Idempotent: safe to re-run. Skips the image build and the corpus seed when
# they are already done, so a re-run after a crash takes seconds rather than
# re-downloading torch.
#
# What it does NOT do: create your .env or supply an LLM API key. Without a
# provider key the retrieval half works and investigations still run to a
# terminal state, but no answer is generated and no hypothesis is formed - see
# DEMO.md.
set -euo pipefail

cd "$(dirname "$0")/.."

RAG_IMAGE="${RAG_IMAGE:-agent-k-rag:v1-good}"
say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }

# --- preflight ---------------------------------------------------------------
say "Preflight"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop (or dockerd) and re-run." >&2
  exit 1
fi
echo "  docker ok"

if [ ! -f .env ]; then
  cp .env.example .env
  warn "created .env from .env.example"
  warn "DEPLOYER_TOKEN is REQUIRED - compose refuses to start any service without it:"
  warn '  python -c "import secrets; print(secrets.token_hex(24))"'
  exit 1
fi

# Compose interpolates ${DEPLOYER_TOKEN:?} and aborts with a cryptic error if it
# is blank, so check it here where the message can actually be useful.
if ! grep -qE '^DEPLOYER_TOKEN=.+' .env; then
  echo "DEPLOYER_TOKEN is empty in .env. Compose will refuse to start. Generate one:" >&2
  echo '  python -c "import secrets; print(secrets.token_hex(24))"' >&2
  exit 1
fi
echo "  .env ok"

if grep -qE '^GROQ_API_KEY=.+|^CEREBRAS_API_KEY=.+|^GEMINI_API_KEY=.+' .env; then
  echo "  provider key present"
else
  warn "no LLM provider key in .env - /ask will not generate answers and"
  warn "investigations will escalate with no claims. Set GROQ_API_KEY to fix."
fi

# --- datastore ---------------------------------------------------------------
say "Starting pgvector Postgres"
docker compose up -d rag-postgres
until [ "$(docker inspect -f '{{.State.Health.Status}}' rag-postgres 2>/dev/null)" = "healthy" ]; do
  sleep 2
done
echo "  rag-postgres healthy"

# --- image -------------------------------------------------------------------
# rag-app has no `build:` stanza in docker-compose.yaml (the image tag is what a
# rollback swaps), so `compose up` would try to pull it. Build explicitly.
if docker image inspect "$RAG_IMAGE" >/dev/null 2>&1; then
  say "Image $RAG_IMAGE already built - skipping (delete it to force a rebuild)"
else
  say "Building $RAG_IMAGE (first run pulls torch - several minutes)"
  docker build -t "$RAG_IMAGE" .
fi

# The rollback demo needs a second tag to roll back *from*. Same image, different
# tag: the "bad deployment" is a runtime config, not a divergent codebase.
if ! docker image inspect agent-k-rag:v2-broken >/dev/null 2>&1; then
  docker tag "$RAG_IMAGE" agent-k-rag:v2-broken
  echo "  tagged agent-k-rag:v2-broken for the rollback demo"
fi

# --- app ---------------------------------------------------------------------
say "Starting rag-app"
docker compose up -d rag-app
until [ "$(docker inspect -f '{{.State.Health.Status}}' rag-app 2>/dev/null)" = "healthy" ]; do
  sleep 2
done
echo "  rag-app healthy"

say "Applying migrations"
docker compose exec -T rag-app alembic upgrade head

say "Seeding the corpus"
SEEDED=$(docker compose exec -T rag-postgres psql -U agentk -tAc \
  'SELECT count(*) FROM documents' 2>/dev/null || echo 0)
if [ "${SEEDED:-0}" -gt 0 ]; then
  echo "  $SEEDED docs already seeded - skipping"
else
  docker compose exec -T rag-app python -m scripts.seed_corpus 2>&1 | tail -1
fi

# --- checks ------------------------------------------------------------------
say "Verifying"
curl -sf localhost:8000/healthz && echo "  /healthz ok"
curl -sf localhost:8000/admin/flags >/dev/null && echo "  /admin/flags ok"

say "Ready"
cat <<'DONE'
  RAG service   http://localhost:8000
  Reports       http://localhost:8000/report

  Next, start the demo UI:
      cd demo && npm install && npm run dev

  Help centre   http://localhost:3000
  Console       http://localhost:3000/console      <- run the four incidents here

  See DEMO.md for the walkthrough.
DONE
