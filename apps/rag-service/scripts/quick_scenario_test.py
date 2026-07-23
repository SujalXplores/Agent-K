"""Quick scenario test — writes results to smoke_results.txt."""

import asyncio
import time

import httpx


async def main():
    results = []
    async with httpx.AsyncClient(timeout=60) as c:
        # 1. Prompt regression
        await c.post(
            "http://localhost:8000/admin/flags/prompt_regression",
            json={"enabled": True},
        )
        r = await c.post(
            "http://localhost:8000/ask",
            json={"question": "How do I reset my password?", "top_k": 3},
        )
        if r.status_code == 200:
            ans = r.json().get("answer", "")[:80]
            results.append(f"Prompt Regression: status=200 answer={ans}")
        else:
            results.append(f"Prompt Regression: FAILED status={r.status_code}")
        await c.post(
            "http://localhost:8000/admin/flags/prompt_regression",
            json={"enabled": False},
        )

        # 2. Retry storm
        await c.post(
            "http://localhost:8000/admin/flags/retry_storm",
            json={"enabled": True},
        )
        try:
            r = await c.post(
                "http://localhost:8000/ask",
                json={"question": "What payment methods do you accept?", "top_k": 3},
                timeout=60,
            )
            d = r.json()
            results.append(
                f"Retry Storm: status={r.status_code} "
                f"tokens_in={d.get('input_tokens', '?')} "
                f"answer={d.get('answer', '')[:80]}"
            )
        except Exception as e:
            results.append(f"Retry Storm: exception={str(e)[:100]}")
        await c.post(
            "http://localhost:8000/admin/flags/retry_storm",
            json={"enabled": False},
        )

        # 3. Retrieval latency
        await c.post(
            "http://localhost:8000/admin/flags/retrieval_latency",
            json={"enabled": True},
        )
        t0 = time.monotonic()
        r = await c.post(
            "http://localhost:8000/ask",
            json={"question": "How do I track my order?", "top_k": 3},
            timeout=60,
        )
        elapsed = time.monotonic() - t0
        d = r.json()
        results.append(
            f"Retrieval Latency: status={r.status_code} "
            f"elapsed={elapsed:.1f}s "
            f"answer={d.get('answer', '')[:80]}"
        )
        await c.post(
            "http://localhost:8000/admin/flags/retrieval_latency",
            json={"enabled": False},
        )

        # 4. Pool exhaustion
        await c.post(
            "http://localhost:8000/admin/flags/pool_exhaustion",
            json={"enabled": True},
        )
        try:
            r = await c.post(
                "http://localhost:8000/ask",
                json={"question": "How do I enable dark mode?", "top_k": 3},
                timeout=30,
            )
            d = r.json()
            results.append(
                f"Pool Exhaustion: status={r.status_code} "
                f"answer={d.get('answer', '')[:80]}"
            )
        except Exception as e:
            results.append(f"Pool Exhaustion: exception={str(e)[:100]}")
        await c.post(
            "http://localhost:8000/admin/flags/pool_exhaustion",
            json={"enabled": False},
        )

        # 5. Deployment marker
        r = await c.post(
            "http://localhost:8000/admin/deploy",
            json={"version": "v2", "note": "smoke test"},
        )
        results.append(f"Deploy Marker: {r.json()['version']}")

    with open("smoke_results.txt", "w") as f:
        for line in results:
            f.write(line + "\n")


if __name__ == "__main__":
    asyncio.run(main())
