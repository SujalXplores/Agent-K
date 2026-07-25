"""The `deployer` sidecar: the sole holder of the Docker socket (LAW2-03/04).

This process exists so that Agent K NEVER holds the Docker socket. Mounting the
socket into Agent K would grant it effective host root, which would make Law 2's
"action stays inside the permitted sandbox" claim a matter of convention (Agent K
promising not to misuse a capability it holds) rather than of structure. Here the
boundary is structural: Agent K's entire worst-case blast radius is ONE
authenticated HTTP call to ONE endpoint that does ONE hardcoded thing.

Design rules this file must keep, each one load-bearing for that claim:

  * EXACTLY ONE mutating endpoint (`POST /rollback`). `GET /healthz` is read-only.
  * The caller supplies NO image reference. The request body is empty by design -
    the sidecar itself determines the previous known-good tag from its own
    configuration. A caller that cannot name an image cannot be tricked into
    deploying an attacker's image.
  * The command is hardcoded `docker compose up -d --force-recreate <service>`,
    built as a fixed argv and run WITHOUT a shell, so no input reaches a shell.
  * `up -d --force-recreate`, NEVER `restart`. `restart` would restart the
    container on its CURRENT image and silently "succeed" while changing nothing -
    the rollback would appear to work and the incident would continue.
  * A concurrency lock: a second rollback while one is in flight gets 409, never a
    racing pair of compose invocations mutating the same service.
  * Auth fails CLOSED. Unlike the RAG app's `/admin/flags` (which is deliberately
    open when ADMIN_TOKEN is unset, a local-demo convenience), an unset
    DEPLOYER_TOKEN here makes the endpoint refuse to serve at all (503). This
    process can mutate running infrastructure; there is no configuration of it
    that should ever be unauthenticated.

The pre-mutation image tag is captured BEFORE the compose invocation and returned
to the caller, so Agent K can record what it rolled back FROM in its own telemetry
without ever needing to inspect Docker itself (LAW2-04).

Live-verification status: this module's contract is fully unit-tested with the
Docker layer faked (see tests/test_deployer.py). Running it against a real Docker
socket needs the RAG app containerized with two versioned image tags, which does
not exist yet - see RUNNING-AGENT-K.md for the human-verification steps.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import os

from fastapi import FastAPI, Header, HTTPException
from opentelemetry import trace
from pydantic import BaseModel

from deployer.constants import (
    DEPLOYER_ROLLBACK_EXIT_CODE,
    DEPLOYER_ROLLBACK_FROM_IMAGE,
    DEPLOYER_ROLLBACK_SERVICE,
    DEPLOYER_ROLLBACK_TO_IMAGE,
    DEPLOYMENT_MARKER_SCENARIO,
    DEPLOYMENT_MARKER_VERSION,
    ROLLBACK_MARKER_SCENARIO,
)

logger = logging.getLogger(__name__)

# --- Configuration (all sidecar-owned; none of it is caller-supplied) ---
COMPOSE_FILE = os.getenv("ROLLBACK_COMPOSE_FILE", "/workspace/docker-compose.yaml")
# The compose PROJECT the running stack belongs to. This is load-bearing: compose
# defaults the project name to the basename of the compose file's directory, which
# inside this sidecar is `/workspace` -> "workspace". The stack it must re-create,
# however, was brought up on the HOST from the repo directory, so it lives under a
# different project (e.g. "agent-k"). Recreating under the wrong project makes
# compose try to CREATE a fresh container on the service's fixed `container_name`,
# which collides with the already-running one ("container name ... is already in
# use") and the rollback fails with a compose exit 1. Passing the real project name
# via `-p` makes the sidecar act on the EXISTING container instead of a phantom new
# stack. Left blank => no `-p` (preserves the bare-argv behaviour the tests pin).
COMPOSE_PROJECT = os.getenv("ROLLBACK_COMPOSE_PROJECT", "").strip()
TARGET_SERVICE = os.getenv("ROLLBACK_TARGET_SERVICE", "rag-app")
TARGET_CONTAINER = os.getenv("ROLLBACK_TARGET_CONTAINER", "rag-app")
# The previous known-good image tag. The SIDECAR knows this; the caller never
# names an image (LAW2-03). Written into the compose env file below so compose
# resolves the service's `image:` interpolation to it on re-create.
KNOWN_GOOD_TAG = os.getenv("ROLLBACK_KNOWN_GOOD_TAG", "v1-good")
IMAGE_TAG_ENV_FILE = os.getenv("ROLLBACK_IMAGE_TAG_ENV_FILE", "/workspace/.env.deploy")
IMAGE_TAG_ENV_VAR = os.getenv("ROLLBACK_IMAGE_TAG_ENV_VAR", "RAG_IMAGE_TAG")
SUBPROCESS_TIMEOUT_S = float(os.getenv("ROLLBACK_TIMEOUT_S", "180"))

app = FastAPI(title="agent-k-deployer")

# Guards the whole capture -> mutate -> marker sequence. Checked non-blockingly so
# a concurrent request gets an immediate 409 rather than queueing behind a
# multi-second compose run.
_rollback_lock = asyncio.Lock()


class RollbackResponse(BaseModel):
    status: str
    service: str
    previous_image: str | None
    rolled_back_to: str


def _token_matches(provided: str | None) -> bool:
    """Constant-time compare against DEPLOYER_TOKEN. Never `==` (timing)."""
    expected = os.getenv("DEPLOYER_TOKEN")
    if not expected or provided is None:
        return False
    return hmac.compare_digest(provided, expected)


async def _run(argv: list[str]) -> tuple[int, str, str]:
    """Run a fixed argv with no shell, returning (exit_code, stdout, stderr).

    `create_subprocess_exec` (not `_shell`) is deliberate: there is no shell to
    inject into even if a configuration value were ever attacker-influenced.
    """
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SUBPROCESS_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def capture_current_image() -> str | None:
    """Read the target container's CURRENT image tag, before any mutation.

    Best-effort: a missing container (already down) returns None rather than
    aborting the rollback - rolling a down service back up to the known-good tag
    is still the correct action. The None is reported honestly to the caller
    instead of being papered over with a fabricated tag.
    """
    try:
        code, out, err = await _run(
            ["docker", "inspect", "--format", "{{.Config.Image}}", TARGET_CONTAINER]
        )
    except (asyncio.TimeoutError, FileNotFoundError, OSError):
        logger.exception("could not inspect target container")
        return None
    if code != 0:
        logger.warning("docker inspect failed: %s", err.strip())
        return None
    return out.strip() or None


def _write_image_tag(tag: str) -> None:
    """Pin the compose image-tag variable to `tag` for the re-create.

    Written as the file's entire contents (single-variable file), so a rollback
    can never accumulate stale lines that a later compose run might read.
    """
    with open(IMAGE_TAG_ENV_FILE, "w", encoding="utf-8") as fh:
        fh.write(f"{IMAGE_TAG_ENV_VAR}={tag}\n")


async def _perform_rollback() -> RollbackResponse:
    """Capture -> pin tag -> force-recreate -> deployment marker (LAW2-03/04)."""
    previous_image = await capture_current_image()

    _write_image_tag(KNOWN_GOOD_TAG)

    # Hardcoded. `up -d --force-recreate`, never `restart` (see module docstring).
    # `-p <project>` (when configured) pins the re-create to the SAME compose
    # project the stack is already running under, so compose acts on the existing
    # container rather than colliding with its fixed container_name.
    argv = ["docker", "compose"]
    if COMPOSE_PROJECT:
        argv += ["-p", COMPOSE_PROJECT]
    argv += [
        "-f",
        COMPOSE_FILE,
        "up",
        "-d",
        "--force-recreate",
        TARGET_SERVICE,
    ]
    try:
        code, _out, err = await _run(argv)
    except asyncio.TimeoutError:
        logger.error("rollback timed out after %.0fs", SUBPROCESS_TIMEOUT_S)
        raise HTTPException(status_code=504, detail="rollback timed out") from None

    _emit_deployment_marker(previous_image, KNOWN_GOOD_TAG, code)

    if code != 0:
        logger.error("rollback failed (exit %d): %s", code, err.strip())
        raise HTTPException(status_code=500, detail=f"compose exited {code}")

    logger.info("rollback complete: %s -> %s", previous_image, KNOWN_GOOD_TAG)
    return RollbackResponse(
        status="rolled_back",
        service=TARGET_SERVICE,
        previous_image=previous_image,
        rolled_back_to=KNOWN_GOOD_TAG,
    )


def _emit_deployment_marker(from_image: str | None, to_image: str, exit_code: int) -> None:
    """Emit the `deployment.marker` span for this mutation (LAW2-04).

    Emitted from the sidecar - the component that actually performed the
    mutation - rather than from Agent K, so the marker's provenance matches
    reality. Emitted on failure too: an ATTEMPTED rollback that did not apply is
    exactly the kind of event an operator reading the trace view needs to see,
    and its exit code distinguishes it from a successful one.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("deployment.marker") as span:
        span.set_attribute(DEPLOYMENT_MARKER_SCENARIO, ROLLBACK_MARKER_SCENARIO)
        span.set_attribute(DEPLOYMENT_MARKER_VERSION, to_image)
        span.set_attribute(DEPLOYER_ROLLBACK_SERVICE, TARGET_SERVICE)
        span.set_attribute(DEPLOYER_ROLLBACK_TO_IMAGE, to_image)
        span.set_attribute(DEPLOYER_ROLLBACK_EXIT_CODE, exit_code)
        if from_image is not None:
            span.set_attribute(DEPLOYER_ROLLBACK_FROM_IMAGE, from_image)


@app.get("/healthz")
async def healthz() -> dict:
    """Read-only liveness. Never mutates; deliberately unauthenticated."""
    return {"status": "ok", "service": TARGET_SERVICE}


@app.post("/rollback", response_model=RollbackResponse)
async def rollback(
    x_deployer_token: str | None = Header(default=None, alias="X-Deployer-Token"),
) -> RollbackResponse:
    """The ONE mutating endpoint (LAW2-03).

    Takes no body: the caller names no image, no service, and no command. Returns
    409 when a rollback is already in flight, 401 on a bad token, 503 when the
    sidecar has no token configured at all.
    """
    if not os.getenv("DEPLOYER_TOKEN"):
        # Fail closed - see the auth rule in the module docstring.
        logger.error("refusing to serve /rollback: DEPLOYER_TOKEN is not configured")
        raise HTTPException(status_code=503, detail="deployer is not configured for authentication")

    if not _token_matches(x_deployer_token):
        raise HTTPException(status_code=401, detail="invalid deployer token")

    # No `await` between the check and the acquire, so this cannot race on the
    # event loop: a second request either sees the lock held (409) or arrives
    # after it is released.
    if _rollback_lock.locked():
        raise HTTPException(status_code=409, detail="a rollback is already in flight")

    async with _rollback_lock:
        return await _perform_rollback()
