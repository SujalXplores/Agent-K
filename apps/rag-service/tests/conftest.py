"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from app.flags import get_flag_store


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def reset_flags() -> AsyncGenerator[None, None]:
    """Reset all feature flags before and after each test."""
    store = get_flag_store()
    await store.reset_all()
    yield
    await store.reset_all()
