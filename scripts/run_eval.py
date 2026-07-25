"""Evaluation harness: 4 seeded incidents x 3 runs (EVAL-01/02).

    python -m scripts.run_eval                 # full 12-run eval
    python -m scripts.run_eval --runs 1        # 4 runs, smoke test
    python -m scripts.run_eval --dry-run       # print the plan, touch nothing

Requires the app on :8000 and a live SigNoz + Groq key.

Per run it records: diagnosis correctness, policy verdict, rollback result,
token cost, time-to-diagnosis, MCP query count. Writes evals/results.json plus a
human-readable summary.

PACING (EVAL-02). Groq's free tier allows 6000 tokens/minute. One investigation
issues 2-4 LLM calls of roughly 1400 tokens, so ~3-5k tokens land in a few
seconds. Two back-to-back investigations therefore breach the limit and return
HTTP 413 - which is how the very first live run failed. RUN_GAP_S paces within a
scenario; it is a floor, not a guess.

CONTAMINATION (read before trusting any number). Agent K diagnoses partly from
deployment.marker spans, which persist in SigNoz after the run that emitted them.
Two mitigations: a deliberately SHORT alert window, and a longer gap between
scenario blocks so the previous scenario's markers age out of it. Neither is
perfect. Any run whose diagnosis could have seen a foreign marker is flagged
`possibly_contaminated` in the results rather than quietly averaged in.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import time
from pathlib import Path

import httpx

from app.flags import DEPLOYMENT_CLASS_FLAGS, FLAG_NAMES

APP = "http://localhost:8000"
OUT = Path(__file__).resolve().parent.parent / "evals"

# Scenario order: the two non-deployment scenarios run FIRST, while SigNoz holds
# the fewest markers. They are the ones a stale marker could wrongly push into an
# "approved" verdict, so they get the cleanest window.
SCENARIOS = ["retrieval_latency", "db_pool_exhaustion", "prompt_regression", "retry_storm"]

ALERT_WINDOW_MIN = 3     # keep tight: shorter window, less foreign-marker exposure
RUN_GAP_S = 75           # within a scenario block — Groq TPM floor
BLOCK_GAP_S = 210        # between scenarios — lets the previous markers age out
TRAFFIC_CALLS = 3        # /ask calls per run, to generate incident telemetry
POLL_TIMEOUT_S = 180


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


async def set_flags(client: httpx.AsyncClient, token: str, active: str | None) -> None:
    """All scenarios OFF, then exactly one ON. Toggling ON is also what emits the
    deployment marker for deployment-class scenarios (FLAG-06)."""
    for name in FLAG_NAMES:
        await client.post(
            f"{APP}/admin/flags",
            headers={"X-Admin-Token": token},
            json={"name": name, "enabled": name == active},
        )


async def generate_traffic(client: httpx.AsyncClient) -> None:
    for _ in range(TRAFFIC_CALLS):
        try:
            await client.post(
                f"{APP}/ask", json={"question": "How do I revoke a leaked API key?"}, timeout=90
            )
        except Exception:
            pass  # a failing /ask IS the incident for some scenarios


async def fire_alert(client: httpx.AsyncClient, scenario: str) -> None:
    starts = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=ALERT_WINDOW_MIN)
    await client.post(
        f"{APP}/alerts/webhook",
        json={
            "receiver": "agent-k-eval",
            "status": "firing",
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "HighErrorRateSLOBurn",
                           "service": "agent-k-rag-service", "severity": "critical"},
                "annotations": {"burn_rate": "2.4", "eval_scenario": scenario},
                "startsAt": starts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }],
        },
    )


async def wait_for_new(client: httpx.AsyncClient, known: set[str]) -> dict | None:
    """Poll until an investigation id we have not seen appears."""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        await asyncio.sleep(4)
        try:
            rows = (await client.get(f"{APP}/api/investigations", timeout=20)).json()
        except Exception:
            continue
        fresh = [r for r in rows if r["id"] not in known]
        if fresh:
            return fresh[0]
    return None


def score(scenario: str, rec: dict, markers_seen: set[str]) -> dict:
    """Grade one run. `correct` compares the diagnosed incident type against the
    scenario actually injected - the only honest definition of correctness here."""
    diagnosed = rec.get("incident_type")
    should_approve = scenario in DEPLOYMENT_CLASS_FLAGS
    verdict = rec.get("verdict")
    foreign = markers_seen - {scenario}
    return {
        "scenario": scenario,
        "diagnosed": diagnosed,
        "correct_diagnosis": diagnosed == scenario,
        "verdict": verdict,
        "expected_verdict": "approved" if should_approve else "denied",
        "verdict_as_expected": (verdict == "approved") == should_approve if verdict else False,
        "failed_checks": rec.get("failed_checks", []),
        "action_status": rec.get("action_status"),
        "action_verified": rec.get("action_verified"),
        "confidence": rec.get("confidence"),
        "tokens": rec.get("total_tokens"),
        "time_to_diagnosis_s": rec.get("duration_s"),
        "mcp_queries": rec.get("mcp_query_count"),
        "mcp_failures": rec.get("mcp_query_failures"),
        "incomplete": rec.get("incomplete"),
        "investigation_id": rec.get("id"),
        # A deployment-class marker from an EARLIER scenario may still be inside
        # this run's window; if so the diagnosis is not cleanly attributable.
        "possibly_contaminated": bool(foreign & DEPLOYMENT_CLASS_FLAGS),
    }


async def main(runs_per_scenario: int, dry_run: bool) -> None:
    token = ""
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ADMIN_TOKEN="):
                token = line.split("=", 1)[1].strip()

    plan = [(s, i + 1) for s in SCENARIOS for i in range(runs_per_scenario)]
    est = len(plan) * RUN_GAP_S + (len(SCENARIOS) - 1) * BLOCK_GAP_S
    log(f"{len(plan)} runs planned, ~{est // 60} min")
    if dry_run:
        for s, i in plan:
            print(f"  {s} run {i}")
        return

    results: list[dict] = []
    markers_seen: set[str] = set()

    async with httpx.AsyncClient(timeout=60) as client:
        known = {r["id"] for r in (await client.get(f"{APP}/api/investigations")).json()}

        for scenario in SCENARIOS:
            if results:
                log(f"--- block gap {BLOCK_GAP_S}s (letting markers age out) ---")
                await asyncio.sleep(BLOCK_GAP_S)
            if scenario in DEPLOYMENT_CLASS_FLAGS:
                markers_seen.add(scenario)

            for run in range(1, runs_per_scenario + 1):
                if run > 1:
                    await asyncio.sleep(RUN_GAP_S)
                log(f"{scenario} run {run}/{runs_per_scenario}")
                await set_flags(client, token, scenario)
                await generate_traffic(client)
                await fire_alert(client, scenario)

                rec = await wait_for_new(client, known)
                if rec is None:
                    log("  TIMED OUT — no investigation appeared")
                    results.append({"scenario": scenario, "error": "timeout"})
                    continue
                known.add(rec["id"])
                row = score(scenario, rec, markers_seen)
                results.append(row)
                log(f"  diagnosed={row['diagnosed']} verdict={row['verdict']} "
                    f"correct={row['correct_diagnosis']} tokens={row['tokens']} "
                    f"{row['time_to_diagnosis_s']:.1f}s"
                    if row.get("time_to_diagnosis_s") else f"  {row}")

        await set_flags(client, token, None)  # leave the service healthy

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    summarize(results)


def summarize(results: list[dict]) -> None:
    graded = [r for r in results if "error" not in r]
    clean = [r for r in graded if not r["possibly_contaminated"]]
    lines = ["# Evaluation results", "",
             f"Runs: {len(results)}  |  graded: {len(graded)}  |  "
             f"uncontaminated: {len(clean)}", ""]

    def pct(rows, key):
        return f"{sum(bool(r[key]) for r in rows)}/{len(rows)}" if rows else "0/0"

    lines += [
        f"- Correct diagnosis (all graded): **{pct(graded, 'correct_diagnosis')}**",
        f"- Correct diagnosis (uncontaminated only): **{pct(clean, 'correct_diagnosis')}**",
        f"- Verdict as expected: **{pct(graded, 'verdict_as_expected')}**",
        "",
        "| Scenario | Run | Diagnosed | Correct | Verdict | Expected | Tokens | Time (s) | Flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    counters: dict[str, int] = {}
    for r in graded:
        counters[r["scenario"]] = counters.get(r["scenario"], 0) + 1
        flags = []
        if r["possibly_contaminated"]:
            flags.append("contaminated?")
        if r["incomplete"]:
            flags.append("incomplete")
        lines.append(
            f"| {r['scenario']} | {counters[r['scenario']]} | {r['diagnosed']} | "
            f"{'yes' if r['correct_diagnosis'] else 'NO'} | {r['verdict']} | "
            f"{r['expected_verdict']} | {r['tokens']} | "
            f"{r['time_to_diagnosis_s']:.1f} | {', '.join(flags) or '-'} |"
        )
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.runs, a.dry_run))
