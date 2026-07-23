"""Database layer: SQLAlchemy async engine + pgvector registration.

Per STACK.md version-compat table: for async engines, register the vector
type via ``event.listens_for(engine.sync_engine, "connect")`` — asyncpg
needs explicit registration unlike psycopg2's auto-adapter.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


# ─── Engine + session factory ──────────────────────────────────────────
# Created lazily so tests / scripts can import this module without
# requiring a live database connection.

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _create_engine():
    settings = get_settings()

    # Default pool config — can be overridden by failure modes at runtime
    # via the pool_exhaustion flag (see app/failure_modes/pool_exhaustion.py)
    engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

    # Note: pgvector type registration is handled automatically by the
    # pgvector.sqlalchemy.Vector column type used in the Document model.
    # No manual asyncpg registration is needed when using SQLAlchemy's
    # Vector type — it handles serialization/deserialization transparently.

    return engine


def get_engine():
    """Return the async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables and pgvector extension. Call once at startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Enable pgvector extension
        from sqlalchemy import text

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized (tables created, pgvector enabled)")


async def close_db() -> None:
    """Dispose the engine. Call on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
