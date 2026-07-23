"""Tests for the feature flag store and admin routes."""

from __future__ import annotations

import pytest

from app.flags import get_flag_store


@pytest.mark.asyncio
async def test_all_flags_start_disabled(reset_flags):
    """All flags should be disabled by default."""
    store = get_flag_store()
    flags = await store.all_flags()

    assert set(flags.keys()) == {
        "prompt_regression",
        "retry_storm",
        "retrieval_latency",
        "pool_exhaustion",
    }
    for name, state in flags.items():
        assert state["enabled"] is False, f"{name} should be disabled"
        assert state["params"] == {}


@pytest.mark.asyncio
async def test_enable_flag(reset_flags):
    """Enabling a flag should set enabled=True and record timestamp."""
    store = get_flag_store()

    await store.set("prompt_regression", True)
    flag = await store.get("prompt_regression")

    assert flag.enabled is True
    assert flag.toggled_at != ""


@pytest.mark.asyncio
async def test_enable_flag_with_params(reset_flags):
    """Enabling a flag with params should store them."""
    store = get_flag_store()

    await store.set("retry_storm", True, {"timeout": 0.3, "retries": 5})
    flag = await store.get("retry_storm")

    assert flag.enabled is True
    assert flag.params["timeout"] == 0.3
    assert flag.params["retries"] == 5


@pytest.mark.asyncio
async def test_disable_flag(reset_flags):
    """Disabling a flag should set enabled=False."""
    store = get_flag_store()

    await store.set("retrieval_latency", True)
    assert (await store.get("retrieval_latency")).enabled is True

    await store.set("retrieval_latency", False)
    assert (await store.get("retrieval_latency")).enabled is False


@pytest.mark.asyncio
async def test_unknown_flag_raises(reset_flags):
    """Requesting an unknown flag should raise KeyError."""
    store = get_flag_store()

    with pytest.raises(KeyError):
        await store.get("nonexistent_flag")


@pytest.mark.asyncio
async def test_reset_all(reset_flags):
    """Resetting all flags should disable everything."""
    store = get_flag_store()

    await store.set("prompt_regression", True)
    await store.set("pool_exhaustion", True)
    assert (await store.get("prompt_regression")).enabled is True

    await store.reset_all()

    for name in ["prompt_regression", "pool_exhaustion", "retry_storm", "retrieval_latency"]:
        assert (await store.get(name)).enabled is False


@pytest.mark.asyncio
async def test_is_enabled_helper(reset_flags):
    """is_enabled should return the current state."""
    store = get_flag_store()

    assert await store.is_enabled("prompt_regression") is False

    await store.set("prompt_regression", True)
    assert await store.is_enabled("prompt_regression") is True
