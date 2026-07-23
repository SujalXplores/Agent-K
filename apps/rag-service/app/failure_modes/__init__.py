"""Failure mode package — four seeded failure scenarios.

Each module exposes:
- ``is_active()`` — check if the flag is enabled
- A function to get the failure-specific config

Flags are toggled via ``/admin/flags/{name}`` without restarting the app.
"""

from app.failure_modes import (
    pool_exhaustion,
    prompt_regression,
    retrieval_latency,
    retry_storm,
)

__all__ = [
    "pool_exhaustion",
    "prompt_regression",
    "retrieval_latency",
    "retry_storm",
]
