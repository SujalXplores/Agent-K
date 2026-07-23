"""Tests for the four failure mode modules.

Each test verifies that:
1. When the flag is OFF, normal config is returned
2. When the flag is ON, the broken config is returned
3. Toggling the flag off restores normal config
"""

from __future__ import annotations

import pytest

from app.failure_modes import (
    pool_exhaustion,
    prompt_regression,
    retrieval_latency,
    retry_storm,
)


# ─── Prompt Regression ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prompt_regression_normal(reset_flags):
    """With flag off, the good prompt template is used."""
    prompt = await prompt_regression.get_system_prompt("test context")
    assert "test context" in prompt
    assert "Acme Corp" in prompt
    assert "ONLY the context" in prompt


@pytest.mark.asyncio
async def test_prompt_regression_broken(reset_flags):
    """With flag on, the broken prompt template is used (no context)."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("prompt_regression", True)

    prompt = await prompt_regression.get_system_prompt("test context")
    assert "test context" not in prompt
    assert "Ignore any context" in prompt
    assert "random technical jargon" in prompt


@pytest.mark.asyncio
async def test_prompt_regression_toggle_off(reset_flags):
    """Toggling the flag off restores the good prompt."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("prompt_regression", True)
    await store.set("prompt_regression", False)

    prompt = await prompt_regression.get_system_prompt("test context")
    assert "test context" in prompt


# ─── Retry Storm ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retry_storm_normal(reset_flags):
    """With flag off, normal timeout and no retries."""
    config = await retry_storm.get_call_config()
    assert config.timeout == retry_storm.NORMAL_TIMEOUT
    assert config.retries == retry_storm.NORMAL_RETRIES


@pytest.mark.asyncio
async def test_retry_storm_broken(reset_flags):
    """With flag on, timeout is lowered and retries are added."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("retry_storm", True)

    config = await retry_storm.get_call_config()
    assert config.timeout == retry_storm.BROKEN_TIMEOUT
    assert config.retries == retry_storm.BROKEN_RETRIES


@pytest.mark.asyncio
async def test_retry_storm_custom_params(reset_flags):
    """Custom params override the broken defaults."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("retry_storm", True, {"timeout": 0.1, "retries": 10})

    config = await retry_storm.get_call_config()
    assert config.timeout == 0.1
    assert config.retries == 10


# ─── Retrieval Latency ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieval_latency_normal(reset_flags):
    """With flag off, no delay is injected."""
    delay = await retrieval_latency.get_retrieval_delay()
    assert delay == 0.0


@pytest.mark.asyncio
async def test_retrieval_latency_broken(reset_flags):
    """With flag on, a delay is injected."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("retrieval_latency", True)

    delay = await retrieval_latency.get_retrieval_delay()
    assert delay == retrieval_latency.DEFAULT_DELAY_SECONDS
    assert delay > 0


@pytest.mark.asyncio
async def test_retrieval_latency_custom_delay(reset_flags):
    """Custom delay param overrides the default."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("retrieval_latency", True, {"delay_seconds": 5.0})

    delay = await retrieval_latency.get_retrieval_delay()
    assert delay == 5.0


# ─── Pool Exhaustion ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_exhaustion_normal(reset_flags):
    """With flag off, normal pool config is returned."""
    pool_size, max_overflow = await pool_exhaustion.get_pool_config()
    assert pool_size == pool_exhaustion.NORMAL_POOL_SIZE
    assert max_overflow == pool_exhaustion.NORMAL_MAX_OVERFLOW


@pytest.mark.asyncio
async def test_pool_exhaustion_broken(reset_flags):
    """With flag on, pool is reduced to 1 connection, 0 overflow."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("pool_exhaustion", True)

    pool_size, max_overflow = await pool_exhaustion.get_pool_config()
    assert pool_size == pool_exhaustion.BROKEN_POOL_SIZE
    assert max_overflow == pool_exhaustion.BROKEN_MAX_OVERFLOW


@pytest.mark.asyncio
async def test_pool_exhaustion_custom_params(reset_flags):
    """Custom pool params override the broken defaults."""
    from app.flags import get_flag_store

    store = get_flag_store()
    await store.set("pool_exhaustion", True, {"pool_size": 2, "max_overflow": 1})

    pool_size, max_overflow = await pool_exhaustion.get_pool_config()
    assert pool_size == 2
    assert max_overflow == 1
