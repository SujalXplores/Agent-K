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

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://agentk:agentk@localhost:5432/agentk"

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
    """FastAPI async dependency yielding an AsyncSession bound to the engine."""
    async with AsyncSessionLocal() as session:
        yield session


def setup_db_instrumentation() -> None:
    """Instrument the engine's sync core so retrieval queries emit DB spans.

    Layers on top of (does not replace) the hand-written rag.retrieval
    span created in app/rag.py (D-07) - call once at application startup,
    after get_engine() has built the engine.
    """
    engine = get_engine()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
