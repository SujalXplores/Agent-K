"""Failure mode: Database Pool Exhaustion (Incident 4).

When this flag is enabled, the SQLAlchemy engine's connection pool is
reduced to size=1, max_overflow=0, causing connection-pool-exhaustion
errors under concurrent load (FLAG-05).

Expected symptom: connection-pool-exhaustion errors in logs, correlated
to failed traces.
Expected verdict: rollback DENIED (rolling back the app version doesn't
fix this class of failure).
"""

from __future__ import annotations

import logging

from app.flags import get_flag_store

logger = logging.getLogger(__name__)

FLAG_NAME = "pool_exhaustion"

# Normal pool config
NORMAL_POOL_SIZE = 10
NORMAL_MAX_OVERFLOW = 20

# Broken pool config (when flag is enabled)
BROKEN_POOL_SIZE = 1
BROKEN_MAX_OVERFLOW = 0


async def get_pool_config() -> tuple[int, int]:
    """Return (pool_size, max_overflow), with broken values if flag is on.

    Note: changing pool config requires recreating the engine. The main
    app calls ``apply_pool_config()`` on startup and when this flag is
    toggled.
    """
    store = get_flag_store()

    if await store.is_enabled(FLAG_NAME):
        params = await store.get_params(FLAG_NAME)
        pool_size = params.get("pool_size", BROKEN_POOL_SIZE)
        max_overflow = params.get("max_overflow", BROKEN_MAX_OVERFLOW)
        logger.warning(
            "Pool exhaustion active — pool_size=%d max_overflow=%d "
            "(will cause connection errors under concurrent load)",
            pool_size,
            max_overflow,
        )
        return pool_size, max_overflow

    return NORMAL_POOL_SIZE, NORMAL_MAX_OVERFLOW


async def is_active() -> bool:
    store = get_flag_store()
    return await store.is_enabled(FLAG_NAME)
