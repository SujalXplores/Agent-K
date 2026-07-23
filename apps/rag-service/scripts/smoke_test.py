# Smoke test script for the RAG support service.
# Run after: docker compose up -d postgres && python -m corpus.generate && uvicorn app.main:app
#
# This script exercises all four failure scenarios by toggling flags
# and hitting the /ask endpoint, then prints what happened.
#
# Usage: python scripts/smoke_test.py

from __future__ import annotations

import asyncio
import json
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
SAMPLE_QUESTION = "How do I reset my password?"


async def toggle_flag(client: httpx.AsyncClient, name: str, enabled: bool, **params):
    """Toggle a feature flag and print the result."""
    body = {"enabled": enabled, "params": params}
    resp = await client.post(f"{BASE_URL}/admin/flags/{name}", json=body)
    print(f"  Flag '{name}' → enabled={enabled} params={params}")
    return resp.json()


async def ask(client: httpx.AsyncClient, question: str = SAMPLE_QUESTION):
    """Send a question to /ask and return the response + timing."""
    start = time.monotonic()
    resp = await client.post(
        f"{BASE_URL}/ask",
        json={"question": question, "top_k": 5},
        timeout=60.0,
    )
    elapsed = time.monotonic() - start
    return resp, elapsed


async def run_scenario(client: httpx.AsyncClient, name: str, flag_name: str):
    """Run a single failure scenario: toggle on, ask, toggle off, ask."""
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"{'='*60}")

    # ─── Baseline (flag off) ─────────────────────────────
    print("\n  [1] Baseline (flag OFF):")
    resp, elapsed = await ask(client)
    if resp.status_code == 200:
        data = resp.json()
        print(f"      Status: OK ({elapsed:.2f}s)")
        print(f"      Answer: {data['answer'][:100]}...")
        print(f"      Tokens: in={data['input_tokens']} out={data['output_tokens']}")
        print(f"      Sources: {len(data['sources'])} docs")
    else:
        print(f"      Status: {resp.status_code} — {resp.text[:100]}")

    # ─── Failure mode (flag on) ──────────────────────────
    print(f"\n  [2] Failure mode (flag ON):")
    await toggle_flag(client, flag_name, True)

    resp, elapsed = await ask(client)
    if resp.status_code == 200:
        data = resp.json()
        print(f"      Status: OK ({elapsed:.2f}s)")
        print(f"      Answer: {data['answer'][:100]}...")
        print(f"      Tokens: in={data['input_tokens']} out={data['output_tokens']}")
    else:
        print(f"      Status: {resp.status_code} — {resp.text[:100]}")
        print(f"      (This may be expected for some failure modes)")

    # ─── Recovery (flag off) ─────────────────────────────
    print(f"\n  [3] Recovery (flag OFF):")
    await toggle_flag(client, flag_name, False)

    resp, elapsed = await ask(client)
    if resp.status_code == 200:
        data = resp.json()
        print(f"      Status: OK ({elapsed:.2f}s)")
        print(f"      Answer: {data['answer'][:100]}...")
    else:
        print(f"      Status: {resp.status_code} — {resp.text[:100]}")


async def main():
    print("Agent K — RAG Support Service Smoke Test")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # ─── Health check ────────────────────────────────────
        print("\n[Health Check]")
        try:
            resp = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if resp.status_code == 200:
                health = resp.json()
                print(f"  Status: {health['status']}")
                print(f"  Version: {health['version']}")
                print(f"  Database: {health['database']}")
                print(f"  Flags: {json.dumps(health['flags'], indent=2)}")
            else:
                print(f"  Health check failed: {resp.status_code}")
                sys.exit(1)
        except httpx.ConnectError:
            print(f"  Cannot connect to {BASE_URL}")
            print("  Is the server running? Start it with:")
            print("    uvicorn app.main:app --reload")
            sys.exit(1)

        # ─── Run all four scenarios ─────────────────────────
        await run_scenario(client, "Prompt Regression", "prompt_regression")
        await run_scenario(client, "Retry Storm", "retry_storm")
        await run_scenario(client, "Retrieval Latency", "retrieval_latency")
        await run_scenario(client, "Pool Exhaustion", "pool_exhaustion")

        # ─── Deployment marker test ─────────────────────────
        print(f"\n{'='*60}")
        print("Deployment Markers")
        print(f"{'='*60}")

        resp = await client.post(
            f"{BASE_URL}/admin/deploy",
            json={"version": "v2", "note": "smoke test deployment"},
        )
        print(f"\n  Created marker: {resp.json()}")

        resp = await client.get(f"{BASE_URL}/admin/deploy")
        print(f"  Markers: {len(resp.json()['markers'])} total")

        # ─── Reset all flags ────────────────────────────────
        await client.post(f"{BASE_URL}/admin/flags/reset")
        print(f"\n  All flags reset.")

    print(f"\n{'='*60}")
    print("Smoke test complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
