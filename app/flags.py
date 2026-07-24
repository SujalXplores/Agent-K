"""In-process feature-flag store for the four seeded failure scenarios (FLAG-01)
plus the deployment-marker emitter that distinguishes deployment-class scenarios
from non-deployment ones (FLAG-06).

Every fault injector (app/rag.py, app/llm.py, app/db.py) reads its flag fresh per
request via is_enabled(), so a toggle through POST /admin/flags takes effect on the
next request with no restart. State is a module-level dict — deliberately in-memory
and non-persistent (matches the CONTEXT.md decision); it resets to all-OFF on process
start so the service can never boot into a degraded posture.

Deployment markers (FLAG-06): SigNoz has no native deployment-marker/annotation API
(SigNoz/signoz#6162, closed unshipped — see 03-RESEARCH.md), so maybe_emit_deployment_marker
emits a custom `deployment.marker` OTel span through the existing OTLP pipeline instead.
The span is emitted ONLY when a deployment-class scenario (prompt_regression, retry_storm)
is toggled ON; the two non-deployment scenarios emit none. That present/absent asymmetry
is the queryable signal the Incident Context dashboard filters on. Attribute names live in
app/observability.py (D-06), never inline here.

The tracer is acquired fresh via trace.get_tracer(__name__) inside the emitter (never
cached at import) so tests' monkeypatched in_memory_exporter provider is observed —
mirroring the established app/rag.py and app/llm.py convention.
"""

from __future__ import annotations

import hmac
import logging
import os

from opentelemetry import trace

from app.observability import DEPLOYMENT_MARKER_SCENARIO, DEPLOYMENT_MARKER_VERSION

logger = logging.getLogger(__name__)

# The four seeded failure scenarios (locked names — injectors key off these exactly).
FLAG_NAMES: tuple[str, ...] = (
    "prompt_regression",
    "retry_storm",
    "retrieval_latency",
    "db_pool_exhaustion",
)

# The scenarios that represent a "deployment" (a code/prompt change) and therefore
# get a deployment.marker span; the other two are runtime/infra faults with no marker.
DEPLOYMENT_CLASS_FLAGS: set[str] = {"prompt_regression", "retry_storm"}

# Module-level store, all-OFF at import. Never boots degraded.
_flags: dict[str, bool] = {name: False for name in FLAG_NAMES}


def is_enabled(name: str) -> bool:
    """Return the flag's current value, read fresh (no caching). Unknown -> False."""
    return _flags.get(name, False)


def set_flag(name: str, enabled: bool) -> None:
    """Set a known flag's value. Raises KeyError for an unknown flag name."""
    if name not in _flags:
        raise KeyError(f"unknown flag name {name!r}; must be one of {list(FLAG_NAMES)}")
    _flags[name] = enabled


def get_all() -> dict[str, bool]:
    """Return a copy of the current state of all four flags."""
    return dict(_flags)


# Env var naming the scenarios a process should boot with already ON, used to build
# the deliberately-broken `v2-broken` image the Law 2 rollback demo rolls back FROM
# (HV-3). See seed_flags_from_env for why this does not weaken the all-OFF default.
SEEDED_FLAGS_ENV = "AGENT_K_SEEDED_FLAGS"


def seed_flags_from_env(raw: str | None = None) -> list[str]:
    """Turn the flags named in AGENT_K_SEEDED_FLAGS ON at boot. Returns those set.

    This does NOT weaken the "never boots degraded" property in the module
    docstring: the default is still all-OFF, and a process can only start degraded
    when an operator explicitly names scenarios in the environment - which is
    precisely what building a known-bad demo image means. Unknown names are ignored
    with a warning rather than raising, so a typo in a compose file degrades to
    "boots healthy" instead of "refuses to boot".
    """
    value = os.getenv(SEEDED_FLAGS_ENV, "") if raw is None else raw
    seeded: list[str] = []
    for name in (part.strip() for part in value.split(",")):
        if not name:
            continue
        if name not in _flags:
            logger.warning("ignoring unknown flag %r in %s", name, SEEDED_FLAGS_ENV)
            continue
        _flags[name] = True
        seeded.append(name)
    if seeded:
        logger.warning("BOOTING WITH FAILURE SCENARIOS ENABLED: %s", ", ".join(seeded))
    return seeded


def token_matches(provided: str | None) -> bool:
    """Constant-time compare `provided` against the ADMIN_TOKEN env var.

    When ADMIN_TOKEN is unset or empty the endpoint is open (returns True for any
    input) — a deliberate local-demo/eval convenience per CONTEXT.md; ADMIN_TOKEN
    must be set for any exposure beyond localhost. Uses hmac.compare_digest, never
    `==`, so a wrong token cannot be distinguished by timing (T-03-02).
    """
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        return True
    if provided is None:
        return False
    return hmac.compare_digest(provided, expected)


def maybe_emit_deployment_marker(flag_name: str, enabled: bool) -> None:
    """Emit a `deployment.marker` span iff a deployment-class scenario toggled ON (FLAG-06).

    Non-deployment scenarios (retrieval_latency, db_pool_exhaustion) and any toggle-OFF
    emit nothing — the present/absent asymmetry IS the signal. No-op for unknown names.
    """
    if not (enabled and flag_name in DEPLOYMENT_CLASS_FLAGS):
        return
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("deployment.marker") as span:
        span.set_attribute(DEPLOYMENT_MARKER_SCENARIO, flag_name)
        span.set_attribute(DEPLOYMENT_MARKER_VERSION, f"flag-toggle-{flag_name}")
