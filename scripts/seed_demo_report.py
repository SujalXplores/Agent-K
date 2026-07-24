"""Seed three SYNTHETIC investigations so the report page can be viewed without
the live alert -> MCP -> LLM -> policy chain.

    python -m scripts.seed_demo_report      # renders build/report-preview/*.html

*** THE DATA THIS WRITES IS FABRICATED. ***

It exists so the report page can be developed, reviewed and screenshotted while
the live path is still being stood up - nothing here queried SigNoz, called a
model, or executed a rollback. Never present output produced by this script as a
real Agent K run: not in the demo video, not in the blog post, not in the eval
results. Every judged artifact must come from a real investigation, which is the
entire point of the project's evidence-integrity rule.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import investigation as inv_module
from app.alerts_webhook import AlertItem
from app.claims import Claim, Evidence
from app.investigation import Investigation, InvestigationState
from app.policy import PolicyCheck, PolicyDecision
from app.rollback import ActionOutcome

SERVICE = "agent-k-rag-service"


def _alert(alertname: str) -> AlertItem:
    return AlertItem(
        status="firing",
        labels={"alertname": alertname, "service": SERVICE},
        annotations={"burn_rate": "2.4"},
        startsAt="2026-07-25T10:14:00Z",
    )


def _evidence(kind: str, ref: str) -> Evidence:
    return Evidence(
        type=kind,
        query=f"query_{kind}s({{'service': '{SERVICE}'}})",
        time_range="2026-07-25T10:14:00Z/now",
        link=f"http://localhost:8080/{kind}/{ref}",
    )


def _checks(deployment_related: bool) -> list[PolicyCheck]:
    return [
        PolicyCheck("slo_breach", True, "burn rate 2.400 vs threshold 1.000"),
        PolicyCheck("allowlist", True, "'rollback' is in allowlist ['rollback']"),
        PolicyCheck("cooldown", True, "no prior action recorded"),
        PolicyCheck("confidence", True, "best evidenced claim confidence vs threshold 0.700"),
        PolicyCheck(
            "deployment_related",
            deployment_related,
            f"incident type {'is' if deployment_related else 'is NOT'} deployment-class",
        ),
        PolicyCheck("sandbox_scope", True, f"target '{SERVICE}' is within sandbox"),
    ]


def build_demo_investigations() -> list[Investigation]:
    """One of each outcome: executed, denied, needs-human."""
    executed = Investigation(id="demo-executed", alert=_alert("HighErrorRateSLOBurn"))
    executed.state = InvestigationState.REPORTED
    executed.claims = [
        Claim(
            claim=(
                "A prompt_regression deployment introduced a malformed system prompt, "
                "driving the answer-generation error rate from 0.4% to 31%."
            ),
            confidence=0.88,
            evidence=[_evidence("trace", "9f2c"), _evidence("log", "svc"), _evidence("metric", "err")],
        )
    ]
    executed.mcp_query_count, executed.total_tokens, executed.duration_s = 3, 4180, 6.42
    executed.policy_decision = PolicyDecision(
        action="rollback", incident_id=executed.id, verdict="approved",
        reason="all policy checks passed", checks=_checks(True),
        slo_value=2.4, confidence=0.88, target_service=SERVICE,
        incident_type="prompt_regression",
        evidence_links=["http://localhost:8080/trace/9f2c"],
    )
    executed.action_outcome = ActionOutcome(
        kind="rollback", status="executed", http_status=200,
        previous_image="agent-k-rag:v2-broken", rolled_back_to="agent-k-rag:v1-good",
        verified=True, verification_detail="error_rate 0.008 at or below 0.05",
    )

    denied = Investigation(id="demo-denied", alert=_alert("RetrievalLatencyP95"))
    denied.state = InvestigationState.REPORTED
    denied.claims = [
        Claim(
            claim=(
                "retrieval_latency: pgvector similarity search p95 rose to 2.1s after the "
                "corpus grew, with no corresponding deployment."
            ),
            confidence=0.81,
            evidence=[_evidence("trace", "3a1f"), _evidence("metric", "p95")],
        )
    ]
    denied.mcp_query_count, denied.total_tokens, denied.duration_s = 3, 3920, 5.87
    denied.policy_decision = PolicyDecision(
        action="rollback", incident_id=denied.id, verdict="denied",
        reason="deployment_related failed", checks=_checks(False),
        slo_value=2.4, confidence=0.81, target_service=SERVICE,
        incident_type="retrieval_latency",
        recommendation=(
            "Agent K did NOT execute rollback. Diagnosed retrieval_latency, but the policy "
            "gate denied the action because — deployment_related: incident type "
            "'retrieval_latency' is NOT deployment-class. A human should review the linked "
            "evidence and decide whether to intervene manually."
        ),
        evidence_links=["http://localhost:8080/trace/3a1f"],
    )

    escalated = Investigation(id="demo-needs-human", alert=_alert("DBPoolExhaustion"))
    escalated.state = InvestigationState.ESCALATED
    escalated.incomplete = True
    escalated.loop_breaker_fired = True
    escalated.watchdog_events = [
        {"kind": "loop_breaker", "query_hash": "8fa3c1d2", "repeat_count": 4}
    ]
    escalated.claims = [
        Claim(
            claim="Partial: connection pool saturation suspected.",
            confidence=0.34,
            evidence=[_evidence("log", "pool")],
        )
    ]
    escalated.mcp_query_count, escalated.mcp_query_failures = 5, 1
    escalated.total_tokens, escalated.duration_s = 8740, 12.10

    return [escalated, denied, executed]


def seed() -> list[Investigation]:
    """Insert the demo investigations into the in-process store."""
    investigations = build_demo_investigations()
    for inv in investigations:
        inv_module._investigations[inv.id] = inv
    return investigations


def render_to(out_dir: Path) -> list[Path]:
    """Render the seeded pages to standalone HTML files for offline review.

    Uses TestClient rather than a live server so this needs no database, no
    provider key, and no running uvicorn - the report routes depend on none of
    them. Output goes to a gitignored directory by default.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    seeded = seed()
    out_dir.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)

    written: list[Path] = []
    for name, path in [("index", "/report"), *((inv.id, f"/report/{inv.id}") for inv in seeded)]:
        response = client.get(path)
        response.raise_for_status()
        target = out_dir / f"{name}.html"
        target.write_text(response.text)
        written.append(target)
    return written


if __name__ == "__main__":
    default_out = Path(__file__).resolve().parent.parent / "build" / "report-preview"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out

    print("*** SYNTHETIC DEMO DATA — never present this as a real Agent K run ***")
    for written in render_to(out):
        print(f"  {written}")
    print(f"\nOpen {out / 'index.html'} in a browser.")
