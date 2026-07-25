"""Async SQLAlchemy engine + session setup for Agent K's RAG datastore.

Mirrors app/telemetry.py's provider-setup module shape: a DEFAULT_*
module constant + a lazily-built module-singleton engine, configured via
load_dotenv() + os.getenv().

Vector serialization for bound query parameters is owned entirely by the
pgvector.sqlalchemy Vector column type declared on app/models.py's
Document.embedding - that type's bind processor already converts a Python
list into the Postgres text form. This module must NOT install a second,
connection-level pgvector codec (e.g. pgvector.asyncpg.register_vector):
the two serialization paths are mutually exclusive, and combining them
makes asyncpg reject the already-serialized parameter with
asyncpg.exceptions.DataError on every vector-bound query
(02-VERIFICATION.md gap 1).

setup_db_instrumentation() instruments the sync core beneath the async
engine with opentelemetry-instrumentation-sqlalchemy so every retrieval
query emits a free DB span (D-07) underneath the hand-written
rag.retrieval span. It must be called once at application startup (wired
in app/main.py).
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import flags
from app.observability import AGENTK_DB_POOL_EXHAUSTED

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://agentk:agentk@localhost:5432/agentk"

# FLAG-05 DB-pool-exhaustion injector. The real SQLAlchemy pool size is fixed at
# engine construction and cannot be resized live without a restart, which would
# violate FLAG-01's no-restart guarantee (03-RESEARCH.md Pitfall 4). Instead, when
# db_pool_exhaustion is ON, an application-level semaphore(1) gates checkout: a
# single in-flight session holds it, and a concurrent second checkout times out
# and raises a pool-exhaustion-shaped error - reproducing the symptom (connection-
# pool-exhaustion errors in logs correlated to failed traces) without ever touching
# the real engine/pool.
_pool_exhaustion_semaphore = asyncio.Semaphore(1)
POOL_ACQUIRE_TIMEOUT_S = 0.1

load_dotenv()
_database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

_engine: AsyncEngine = create_async_engine(_database_url)


AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


def get_engine() -> AsyncEngine:
    """Return the module-singleton async SQLAlchemy engine."""
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI async dependency yielding an AsyncSession bound to the engine.

    FLAG-05: when db_pool_exhaustion is ON, checkout is gated by an application-
    level semaphore(1) (read fresh, no-restart). A concurrent second checkout that
    cannot acquire within POOL_ACQUIRE_TIMEOUT_S raises a pool-exhaustion-shaped
    TimeoutError, logs it, and flags AGENTK_DB_POOL_EXHAUSTED on the active span.
    When OFF, the original checkout path is untouched. The real engine/pool is
    never reconstructed or resized, and no pgvector connection-level codec is added
    (see the module header rule).
    """
    if not flags.is_enabled("db_pool_exhaustion"):
        async with AsyncSessionLocal() as session:
            yield session
        return

    try:
        await asyncio.wait_for(
            _pool_exhaustion_semaphore.acquire(), timeout=POOL_ACQUIRE_TIMEOUT_S
        )
    except TimeoutError as exc:
        logger.error("simulated DB pool exhaustion: checkout timed out")
        trace.get_current_span().set_attribute(AGENTK_DB_POOL_EXHAUSTED, True)
        raise TimeoutError("simulated DB pool exhaustion") from exc

    try:
        async with AsyncSessionLocal() as session:
            yield session
    finally:
        _pool_exhaustion_semaphore.release()


def setup_db_instrumentation() -> None:
    """Instrument the engine's sync core so retrieval queries emit DB spans.

    Layers on top of (does not replace) the hand-written rag.retrieval
    span created in app/rag.py (D-07) - call once at application startup,
    after get_engine() has built the engine.
    """
    engine = get_engine()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
