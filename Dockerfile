# The monitored RAG service. Built into two tags for the Law 2 rollback demo:
#
#   agent-k-rag:v1-good    - built as-is
#   agent-k-rag:v2-broken  - same image, AGENT_K_SEEDED_FLAGS=prompt_regression
#
# Both tags are the SAME SOURCE. The "bad deployment" is a configuration applied at
# run time, not a second codebase - so the rollback demonstrates exactly what a real
# rollback does (swap the running artifact back) without maintaining a divergent branch.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache

WORKDIR /srv

# Build tools are needed by some wheels but not at run time; dropped in the same
# layer so they never reach the final image.
COPY requirements.txt .
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y --auto-remove build-essential \
 && rm -rf /var/lib/apt/lists/*

# Bake the embedding model into the image. Without this the first /ask after a
# rollback would block on a model download - turning a demo about recovery time
# into a demo about Hugging Face's CDN, and failing outright with no network.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2')"

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY signoz-mcp-server-linux ./signoz-mcp-server

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
