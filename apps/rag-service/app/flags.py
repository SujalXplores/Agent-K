"""In-process feature flag store for toggling failure scenarios live.

Per ARCHITECTURE.md Anti-Pattern 2: flag toggle and deployment-marker
creation must be *separable*. Toggling a flag does NOT auto-create a
deployment marker — markers are created via a separate ``/admin/deploy``
call. This preserves the distinction Agent K's policy gate depends on
(Incidents 1/2 are deployment-caused; 3/4 are not).

Flags are toggled via HTTP without restarting the app (FLAG-01).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ─── Flag definitions ─────────────────────────────────────────────────

FLAG_NAMES = frozenset(
    {
        "prompt_regression",
        "retry_storm",
        "retrieval_latency",
        "pool_exhaustion",
    }
)


@dataclass
class FlagState:
    """State of a single feature flag."""

    enabled: bool = False
    params: dict[str, Any] = field(default_factory=dict)
    toggled_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "params": self.params,
            "toggled_at": self.toggled_at,
        }


class FeatureFlagStore:
    """Thread-safe in-memory feature flag store."""

    def __init__(self) -> None:
        self._flags: dict[str, FlagState] = {
            name: FlagState() for name in FLAG_NAMES
        }
        self._lock = asyncio.Lock()

    async def get(self, name: str) -> FlagState:
        if name not in self._flags:
            raise KeyError(f"Unknown flag: {name}")
        return self._flags[name]

    async def is_enabled(self, name: str) -> bool:
        flag = await self.get(name)
        return flag.enabled

    async def get_params(self, name: str) -> dict[str, Any]:
        flag = await self.get(name)
        return flag.params

    async def set(
        self, name: str, enabled: bool, params: dict[str, Any] | None = None
    ) -> FlagState:
        if name not in self._flags:
            raise KeyError(f"Unknown flag: {name}")

        async with self._lock:
            flag = self._flags[name]
            flag.enabled = enabled
            if params is not None:
                flag.params = params
            flag.toggled_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                "Flag '%s' set to enabled=%s params=%s",
                name,
                enabled,
                flag.params,
            )
            return flag

    async def all_flags(self) -> dict[str, dict[str, Any]]:
        return {name: flag.to_dict() for name, flag in self._flags.items()}

    async def reset_all(self) -> None:
        """Disable all flags (used in tests / demo reset)."""
        async with self._lock:
            for flag in self._flags.values():
                flag.enabled = False
                flag.params = {}
                flag.toggled_at = ""


# ─── Singleton ────────────────────────────────────────────────────────

_store: FeatureFlagStore | None = None


def get_flag_store() -> FeatureFlagStore:
    global _store
    if _store is None:
        _store = FeatureFlagStore()
    return _store


# ─── FastAPI routes ───────────────────────────────────────────────────

router = APIRouter(prefix="/admin/flags", tags=["admin"])


class FlagUpdateRequest(BaseModel):
    enabled: bool
    params: dict[str, Any] = {}


@router.get("")
async def list_flags() -> dict[str, Any]:
    """List all feature flags and their current state."""
    store = get_flag_store()
    return await store.all_flags()


@router.get("/{flag_name}")
async def get_flag(flag_name: str) -> dict[str, Any]:
    """Get the state of a single flag."""
    store = get_flag_store()
    try:
        flag = await store.get(flag_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown flag: {flag_name}")
    return flag.to_dict()


@router.post("/{flag_name}")
async def set_flag(flag_name: str, body: FlagUpdateRequest) -> dict[str, Any]:
    """Toggle a flag on/off with optional parameters."""
    store = get_flag_store()
    try:
        flag = await store.set(flag_name, body.enabled, body.params)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown flag: {flag_name}")
    return flag.to_dict()


@router.post("/reset")
async def reset_flags() -> dict[str, str]:
    """Disable all flags at once."""
    store = get_flag_store()
    await store.reset_all()
    return {"status": "all flags disabled"}
