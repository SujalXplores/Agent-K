"""Async SQLAlchemy engine + session setup for Agent K's RAG datastore.

Mirrors app/telemetry.py's provider-setup module shape: a DEFAULT_*
module constant + a lazily-built module-singleton engine, configured via
load_dotenv() + os.getenv(). Registers the pgvector adapter type on
every new connection (asyncpg needs this explicitly, unlike psycopg2's
auto-adapter - CLAUDE.md Version Compatibility) and instruments the
sync engine underneath the async engine with
opentelemetry-instrumentation-sqlalchemy so every retrieval query gets
a free DB span (D-07) underneath the hand-written rag.retrieval span.
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from pgvector.asyncpg import register_vector
from sqlalchemy import event
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


@event.listens_for(_engine.sync_engine, "connect")
def _register_vector_type(dbapi_connection, connection_record):
    """Register the pgvector adapter type on every new connection.

    asyncpg (unlike psycopg2) has no automatic adapter for the vector
    type and requires this explicit registration - CLAUDE.md Version
    Compatibility.
    """
    dbapi_connection.run_async(register_vector)


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
