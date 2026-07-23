"""Failure mode: Retrieval Latency Injection (Incident 3).

When this flag is enabled, artificial delay is added to the pgvector
retrieval query, visibly slowing retrieval spans in the trace waterfall
with no deployment-related cause (FLAG-04).

Expected symptom: retrieval spans slow down, overall latency rises.
Expected verdict: rollback DENIED (not deployment-caused).
"""

from __future__ import annotations

import logging

from app.flags import get_flag_store

logger = logging.getLogger(__name__)

FLAG_NAME = "retrieval_latency"

# Normal: no delay. Broken: 2-3 second delay.
DEFAULT_DELAY_SECONDS = 2.5


async def get_retrieval_delay() -> float:
    """Return the artificial delay to inject before retrieval, if flag is on."""
    store = get_flag_store()

    if await store.is_enabled(FLAG_NAME):
        params = await store.get_params(FLAG_NAME)
        delay = params.get("delay_seconds", DEFAULT_DELAY_SECONDS)
        logger.warning(
            "Retrieval latency injection active — adding %.1fs delay", delay
        )
        return float(delay)

    return 0.0


async def is_active() -> bool:
    store = get_flag_store()
    return await store.is_enabled(FLAG_NAME)
