#!/usr/bin/env python
"""Validate .env before docker compose / uvicorn fails with a cryptic error.

    python scripts/check_env.py

Checks, in order of how early they would bite:
  1. .env exists
  2. DEPLOYER_TOKEN is non-empty (compose refuses to start without it)
  3. At least one LLM provider key is set (Groq / Cerebras / Gemini)
  4. DATABASE_URL is reachable (if rag-postgres is up)
  5. SIGNOZ_URL is reachable (if SigNoz is up)

Each check prints a green OK or a yellow WARNING / red FAIL. Exits non-zero if
any FAIL-level check fails, zero if only WARNINGs remain. This lets demo_up.py
and the Makefile gate on it without blocking on optional services being down.

Designed to be fast: network checks are skipped when the target is not
reachable, and each has a 3-second timeout so the whole script finishes in
under 5 seconds on a cold machine.
"""

from __future__ import annotations

import re
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {_GREEN}OK{_RESET}   {msg}")


def warn(msg: str) -> None:
    print(f"  {_YELLOW}WARN {_RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {_RED}FAIL {_RESET} {msg}")


def read_env() -> dict[str, str]:
    """Parse .env into a dict (simple KEY=VALUE, no quotes/comments)."""
    env: dict[str, str] = {}
    env_file = ROOT / ".env"
    if not env_file.exists():
        return env
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def url_reachable(url: str, timeout_s: float = 3.0) -> bool:
    """Best-effort: is the URL's host:port accepting connections?"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except (OSError, ValueError):
        return False


def main() -> int:
    has_fail = False
    env = read_env()

    # 1. .env exists
    env_file = ROOT / ".env"
    if not env_file.exists():
        fail(".env not found. Run: cp .env.example .env")
        return 1
    ok(".env exists")

    # 2. DEPLOYER_TOKEN
    if env.get("DEPLOYER_TOKEN"):
        ok("DEPLOYER_TOKEN is set")
    else:
        fail("DEPLOYER_TOKEN is empty. Compose refuses to start without it.")
        fail('  Generate: python -c "import secrets; print(secrets.token_hex(24))"')
        has_fail = True

    # 3. LLM provider key
    provider_keys = {
        "GROQ_API_KEY": "groq",
        "CEREBRAS_API_KEY": "cerebras",
        "GEMINI_API_KEY": "gemini",
    }
    configured = [name for key, name in provider_keys.items() if env.get(key)]
    if configured:
        ok(f"LLM provider key present: {', '.join(configured)}")
    else:
        warn("no LLM provider key set - /ask will not generate answers")
        warn("  Set GROQ_API_KEY (or CEREBRAS_API_KEY / GEMINI_API_KEY) in .env")

    # 4. DATABASE_URL reachability
    db_url = env.get("DATABASE_URL", "postgresql+asyncpg://agentk:agentk@localhost:5432/agentk")
    # Extract host:port from the URL for a quick socket check.
    db_host = "localhost"
    db_port = 5432
    match = re.search(r"@([^:/]+):(\d+)", db_url)
    if match:
        db_host, db_port = match.group(1), int(match.group(2))
    try:
        with socket.create_connection((db_host, db_port), timeout=3):
            ok(f"DATABASE_URL reachable ({db_host}:{db_port})")
    except OSError:
        warn(f"DATABASE_URL not reachable ({db_host}:{db_port}) - start with: docker compose up -d rag-postgres")

    # 5. SIGNOZ_URL reachability
    signoz_url = env.get("SIGNOZ_URL", "http://localhost:8080")
    if signoz_url:
        if url_reachable(signoz_url):
            ok(f"SIGNOZ_URL reachable ({signoz_url})")
        else:
            warn(f"SIGNOZ_URL not reachable ({signoz_url}) - start with: foundryctl cast -f casting.yaml")

    print()
    if has_fail:
        fail("One or more required checks failed. Fix the .env issues above.")
        return 1
    ok("Environment checks complete (warnings are OK to ignore for local dev).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
