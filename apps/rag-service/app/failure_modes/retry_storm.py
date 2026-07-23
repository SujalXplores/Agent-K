"""Failure mode: Retry Storm / Cost Runaway (Incident 2).

When this flag is enabled, the LLM client timeout is lowered to ~0.5s and
a retry loop is added, causing repeated LLM calls. User-facing errors may
stay low, but LLM calls/tokens/cost per minute spike and breach the cost
SLO (FLAG-03).

Expected symptom: spiked call count / token usage / cost.
Expected verdict: rollback ALLOWED (deployment-caused, cost SLO breached).

Important differentiator: no HTTP errors needed — a cost SLO alone can
justify a controlled rollback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.flags import get_flag_store

logger = logging.getLogger(__name__)

FLAG_NAME = "retry_storm"

# Normal config
NORMAL_TIMEOUT = 30.0
NORMAL_RETRIES = 0

# Broken config (when flag is enabled)
BROKEN_TIMEOUT = 0.5  # 500ms — too short for most LLM responses
BROKEN_RETRIES = 4  # 1 initial + 4 retries = 5 calls per request


@dataclass
class LLMCallConfig:
    timeout: float | None
    retries: int


async def get_call_config() -> LLMCallConfig:
    """Return the LLM call config, with broken values if flag is on."""
    store = get_flag_store()

    if await store.is_enabled(FLAG_NAME):
        params = await store.get_params(FLAG_NAME)
        timeout = params.get("timeout", BROKEN_TIMEOUT)
        retries = params.get("retries", BROKEN_RETRIES)
        logger.warning(
            "Retry storm active — timeout=%.1fs retries=%d (will cause "
            "repeated LLM calls and cost spike)",
            timeout,
            retries,
        )
        return LLMCallConfig(timeout=timeout, retries=retries)

    return LLMCallConfig(timeout=NORMAL_TIMEOUT, retries=NORMAL_RETRIES)


async def is_active() -> bool:
    store = get_flag_store()
    return await store.is_enabled(FLAG_NAME)
