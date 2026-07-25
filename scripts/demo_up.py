#!/usr/bin/env python
"""Cross-platform demo bring-up: the whole backend in one command.

Replaces scripts/demo_up.sh with a Python implementation that works on Windows
(PowerShell/cmd) and Unix alike. Python is already a hard prerequisite for this
project, so this adds no new dependency.

    python scripts/demo_up.py

Idempotent: safe to re-run. Skips the image build and the corpus seed when they
are already done, so a re-run after a crash takes seconds rather than
re-downloading torch.

What it does NOT do: create your .env or supply an LLM API key. Without a
provider key the retrieval half works and investigations still run to a terminal
state, but no answer is generated and no hypothesis is formed - see DEMO.md.

Environment overrides:
    RAG_IMAGE   Docker image tag for the RAG app (default: agent-k-rag:v1-good)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Repo root is the parent of the scripts/ directory.
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

RAG_IMAGE = os.environ.get("RAG_IMAGE", "agent-k-rag:v1-good")

# ANSI color helpers (work on Windows 10+ terminals; degrade gracefully on older).
_BOLD = "\033[1m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_RESET = "\033[0m"


def say(msg: str) -> None:
    print(f"\n{_BOLD}==> {msg}{_RESET}")


def ok(msg: str) -> None:
    print(f"  {_GREEN}{msg}{_RESET}")


def warn(msg: str) -> None:
    print(f"  {_YELLOW}! {msg}{_RESET}")


def fail(msg: str) -> None:
    print(f"  {_YELLOW}! {msg}{_RESET}", file=sys.stderr)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, raising on failure. kwargs forwarded to subprocess.run."""
    return subprocess.run(cmd, check=True, **kwargs)


def run_quiet(cmd: list[str]) -> subprocess.CompletedProcess | None:
    """Run a command, returning None on failure instead of raising."""
    return subprocess.run(cmd, capture_output=True, text=True)


def docker_container_healthy(name: str, timeout_s: int = 120) -> bool:
    """Wait for a Docker container's health status to become 'healthy'."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = run_quiet([
            "docker", "inspect",
            "-f", "{{.State.Health.Status}}",
            name,
        ])
        if result and result.stdout.strip() == "healthy":
            return True
        time.sleep(2)
    return False


def read_env_value(key: str) -> str | None:
    """Read a value from .env (simple KEY=VALUE parsing, no quotes/comments)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    pattern = re.compile(rf"^{re.escape(key)}=(.+)$")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def check_docker() -> bool:
    """Verify Docker is running."""
    result = run_quiet(["docker", "info"])
    return result is not None and result.returncode == 0


def docker_image_exists(tag: str) -> bool:
    """Check if a Docker image tag exists locally."""
    result = run_quiet(["docker", "image", "inspect", tag])
    return result is not None and result.returncode == 0


def psql_count_documents() -> int:
    """Count rows in the documents table via psql in the rag-postgres container."""
    result = run_quiet([
        "docker", "compose", "exec", "-T", "rag-postgres",
        "psql", "-U", "agentk", "-tAc",
        "SELECT count(*) FROM documents",
    ])
    if result and result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    return 0


def main() -> int:
    # --- preflight ----------------------------------------------------------
    say("Preflight")

    if not check_docker():
        fail("Docker is not running. Start Docker Desktop (or dockerd) and re-run.")
        return 1
    ok("docker ok")

    env_file = ROOT / ".env"
    if not env_file.exists():
        import shutil
        shutil.copy(ROOT / ".env.example", env_file)
        warn("created .env from .env.example")
        warn("DEPLOYER_TOKEN is REQUIRED - compose refuses to start any service without it:")
        warn('  python -c "import secrets; print(secrets.token_hex(24))"')
        return 1

    deployer_token = read_env_value("DEPLOYER_TOKEN")
    if not deployer_token:
        fail("DEPLOYER_TOKEN is empty in .env. Compose will refuse to start. Generate one:")
        fail('  python -c "import secrets; print(secrets.token_hex(24))"')
        return 1
    ok(".env ok")

    has_provider_key = any(
        read_env_value(key) for key in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY")
    )
    if has_provider_key:
        ok("provider key present")
    else:
        warn("no LLM provider key in .env - /ask will not generate answers and")
        warn("investigations will escalate with no claims. Set GROQ_API_KEY to fix.")

    # --- datastore ----------------------------------------------------------
    say("Starting pgvector Postgres")
    run(["docker", "compose", "up", "-d", "rag-postgres"])
    if not docker_container_healthy("rag-postgres"):
        fail("rag-postgres did not become healthy within 120s")
        return 1
    ok("rag-postgres healthy")

    # --- image --------------------------------------------------------------
    if docker_image_exists(RAG_IMAGE):
        say(f"Image {RAG_IMAGE} already built - skipping (delete it to force a rebuild)")
    else:
        say(f"Building {RAG_IMAGE} (first run pulls torch - several minutes)")
        run(["docker", "build", "-t", RAG_IMAGE, "."])

    if not docker_image_exists("agent-k-rag:v2-broken"):
        run(["docker", "tag", RAG_IMAGE, "agent-k-rag:v2-broken"])
        ok("tagged agent-k-rag:v2-broken for the rollback demo")

    # --- app ----------------------------------------------------------------
    say("Starting rag-app")
    run(["docker", "compose", "up", "-d", "rag-app"])
    if not docker_container_healthy("rag-app"):
        fail("rag-app did not become healthy within 120s")
        return 1
    ok("rag-app healthy")

    say("Applying migrations")
    run(["docker", "compose", "exec", "-T", "rag-app", "alembic", "upgrade", "head"])

    say("Seeding the corpus")
    doc_count = psql_count_documents()
    if doc_count > 0:
        ok(f"{doc_count} docs already seeded - skipping")
    else:
        run(["docker", "compose", "exec", "-T", "rag-app", "python", "-m", "scripts.seed_corpus"])

    # --- checks -------------------------------------------------------------
    say("Verifying")
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/healthz", timeout=5)
        ok("/healthz ok")
    except Exception:
        fail("/healthz not reachable")
    try:
        urllib.request.urlopen("http://localhost:8000/admin/flags", timeout=5)
        ok("/admin/flags ok")
    except Exception:
        fail("/admin/flags not reachable")

    say("Ready")
    print("""
  RAG service   http://localhost:8000
  Reports       http://localhost:8000/report

  Next, start the demo UI:
      cd demo && npm install && npm run dev

  Help centre   http://localhost:3000
  Console       http://localhost:3000/console      <- run the four incidents here

  See DEMO.md for the walkthrough.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
