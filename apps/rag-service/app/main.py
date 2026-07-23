"""FastAPI application: the monitored RAG support service.

This is the "patient" — the app that Agent K will later investigate.
It serves ``POST /ask`` (retrieve docs → generate answer), exposes
``/admin/flags/*`` for toggling failure scenarios, and ``/admin/deploy``
for recording deployment markers.

Every step of the pipeline is instrumented with OpenTelemetry:
- HTTP request span (auto-instrumented by FastAPIInstrumentor)
- Retrieval span (manual, in retrieval.py)
- LLM call span (manual, in llm_client.py, with gen_ai.* attributes)
- Deployment marker span (manual, in deploy.py)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import (
    SQLAlchemyInstrumentor,
)
from pydantic import BaseModel
from sqlalchemy import text

from app import deploy, flags
from app.config import get_settings
from app.db import close_db, get_engine, init_db
from app.failure_modes import (
    pool_exhaustion,
    prompt_regression,
    retrieval_latency,
    retry_storm,
)
from app.otel import get_tracer, init_otel
from app.retrieval import retrieve, seed_corpus

logger = logging.getLogger(__name__)

# ─── Request / response models ────────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    version: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    flags: dict[str, Any]


# ─── Lifespan: startup + shutdown ──────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize OTel, database, and seed corpus on startup."""
    # 1. Initialize OpenTelemetry first (everything else needs it)
    init_otel()

    # 2. Configure Python logging with OTel correlation
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    LoggingInstrumentor().instrument()

    # 3. Instrument SQLAlchemy (auto-spans for DB queries)
    engine = get_engine()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    # 4. Initialize database (create extension + tables)
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)
        logger.warning(
            "App will start but /ask will fail until the database is available. "
            "Run: docker compose up -d postgres"
        )

    # 5. Seed corpus (best-effort — may fail if DB not ready)
    try:
        count = await seed_corpus()
        logger.info("Corpus seeded: %d documents", count)
    except Exception as exc:
        logger.error("Failed to seed corpus: %s", exc)
        logger.warning("Run `python -m app.retrieval seed` manually after DB is ready")

    logger.info("RAG support service started (version=%s)", get_settings().app_version)

    yield

    # Shutdown
    await close_db()
    logger.info("RAG support service stopped")


# ─── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agent K — Monitored RAG Support Service",
    description="A deliberately breakable RAG support-answering service for the Agent K hackathon demo.",
    version="1.0.0",
    lifespan=lifespan,
)

# Auto-instrument FastAPI (creates a span for every HTTP request)
FastAPIInstrumentor.instrument_app(app)

# Mount admin routes
app.include_router(flags.router)
app.include_router(deploy.router)


# ─── Routes ───────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check — reports app version, database status, and flag states."""
    settings = get_settings()
    store = flags.get_flag_store()

    # Check database connectivity
    db_status = "unknown"
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.app_version,
        database=db_status,
        flags=await store.all_flags(),
    )


@app.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    """Answer a support question using RAG (retrieve → generate).

    This endpoint checks each failure flag at the relevant step:
    - retrieval_latency: injects delay before the DB query
    - prompt_regression: swaps to a broken prompt template
    - retry_storm: lowers timeout + adds retries to the LLM call
    - pool_exhaustion: reduces DB connection pool (applied at engine level)
    """
    settings = get_settings()
    tracer = get_tracer()

    with tracer.start_as_current_span("rag.ask") as span:
        span.set_attribute("rag.question", body.question[:200])
        span.set_attribute("rag.top_k", body.top_k)
        span.set_attribute("app.version", settings.app_version)

        # ─── Step 1: Retrieve ─────────────────────────────────
        # Check retrieval_latency flag for injected delay
        delay = await retrieval_latency.get_retrieval_delay()

        try:
            docs = await retrieve(
                body.question,
                top_k=body.top_k,
                delay_seconds=delay,
            )
        except Exception as exc:
            span.set_attribute("rag.error", str(exc)[:200])
            logger.error("Retrieval failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Retrieval failed: {exc}",
            ) from exc

        if not docs:
            span.set_attribute("rag.retrieval.empty", True)

        # ─── Step 2: Build context + prompt ────────────────────
        context = "\n\n".join(
            f"[Doc {d['id']}] {d['title']}\n{d['content']}" for d in docs
        )

        # Check prompt_regression flag for broken template
        system_prompt = await prompt_regression.get_system_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": body.question},
        ]

        # ─── Step 3: Generate answer ──────────────────────────
        # Check retry_storm flag for broken timeout/retries
        call_config = await retry_storm.get_call_config()

        from app.llm_client import generate_completion

        try:
            llm_response = await generate_completion(
                messages,
                timeout=call_config.timeout,
                retries=call_config.retries,
            )
        except Exception as exc:
            span.set_attribute("rag.error", str(exc)[:200])
            span.set_attribute("rag.generation.failed", True)
            logger.error("LLM generation failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail=f"LLM generation failed: {exc}",
            ) from exc

        span.set_attribute("rag.answer_length", len(llm_response.text))

        return AskResponse(
            answer=llm_response.text,
            sources=[
                {
                    "id": d["id"],
                    "title": d["title"],
                    "category": d["category"],
                    "distance": round(d["distance"], 4),
                }
                for d in docs
            ],
            model=llm_response.model,
            provider=llm_response.provider,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            version=settings.app_version,
        )


@app.post("/admin/seed")
async def reseed_corpus() -> dict:
    """Re-seed the corpus (useful after clearing the database)."""
    count = await seed_corpus()
    return {"status": "ok", "documents_seeded": count}


@app.get("/admin/version")
async def get_version() -> dict:
    """Get the current app version."""
    return {"version": get_settings().app_version}
