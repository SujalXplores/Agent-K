"""Law 1 evidence-backed claim schema: Evidence, Claim, confidence recalibration,
unevidenced-claim stripping, and SigNoz evidence-link construction (LAW1-01/02/03).

Every claim Agent K could publish carries claim text, a hybrid confidence value, the
SigNoz query used, the time range searched, and a resolvable evidence link
(LAW1-01) - this module is the structural enforcement of that rule: a Claim simply
cannot be constructed without at least attempting an evidence list, and
strip_unevidenced_claims() is the report-renderer-side backstop that removes any
claim whose evidence list is empty before it would ever be shown (LAW1-02) - Agent K
cannot publish an unsupported claim no matter what upstream code does.

Confidence is hybrid-scored (LAW1-03): the LLM proposes an initial value inside
app/investigation.py's hypothesis step, and recalibrate_confidence() here is the
CODE side of that scoring - it adjusts the LLM's number based on evidence
strength/count, so Law 1 is genuinely code-enforced rather than trusting a
self-reported model confidence.

build_evidence_link()'s exact SigNoz UI URL paths (trace/log/metric explorer routes)
are this module's one live-verification gap: they are built from SigNoz's publicly
documented URL conventions but have not been confirmed against a running instance in
this environment (paired with LAW1-05's link-checker, itself a live-verification
step - see scripts/check_evidence_links.py).
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

# Recalibration weights (LAW1-03). Deliberately simple, additive adjustments over
# the LLM's proposed value rather than a learned model - Law 1 must be auditable
# code, not another opaque scoring pass.
DEPLOYMENT_MARKER_CONFIDENCE_BOOST = 0.15
PER_EVIDENCE_ITEM_BOOST = 0.05
MAX_EVIDENCE_ITEMS_COUNTED = 4  # boost caps out past this many corroborating items
ERROR_RATE_DELTA_BOOST_SCALE = 0.20  # full boost at delta >= 1.0 (i.e. +100pp)

# Recalibration may raise confidence, but never to certainty. A first live run
# produced a rendered "Confidence 100%" claim - the model proposed 0.9 and the
# boosts clamped to 1.0 - on a diagnosis that was in fact WRONG. No finite set of
# correlational evidence justifies claiming certainty about a root cause, and a
# system whose entire pitch is calibrated, evidence-backed honesty is damaged more
# by one overconfident claim than by a hundred appropriately hedged ones.
MAX_RECALIBRATED_CONFIDENCE = 0.95


class Evidence(BaseModel):
    """One resolvable piece of SigNoz evidence backing a claim (LAW1-01)."""

    type: str  # "trace" | "log" | "metric" | "deployment"
    query: str  # the SigNoz/MCP query used, verbatim (tool name + arguments)
    time_range: str  # e.g. "2026-07-24T10:00:00Z/2026-07-24T10:15:00Z"
    link: str  # a resolvable SigNoz deep link (see build_evidence_link)


class Claim(BaseModel):
    """A single root-cause hypothesis Agent K could publish (LAW1-01)."""

    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)


def strip_unevidenced_claims(claims: list[Claim]) -> list[Claim]:
    """Remove any claim with an empty evidence list (LAW1-02).

    This is the report-renderer-side backstop: even if something upstream
    constructs a Claim with no evidence, it is filtered out here before ever
    being shown - Agent K cannot publish an unsupported claim.
    """
    return [c for c in claims if c.evidence]


def recalibrate_confidence(
    llm_confidence: float,
    evidence: list[Evidence],
    deployment_marker_present: bool = False,
    error_rate_delta: float | None = None,
) -> float:
    """Code-recalibrate an LLM-proposed confidence value (LAW1-03).

    Starts from the LLM's proposed value and applies bounded, auditable additive
    adjustments: a deployment-marker boost (a deployment-class incident with a
    corresponding marker is strong corroborating evidence), a per-evidence-item
    boost (more corroborating queries -> more confidence, capped at
    MAX_EVIDENCE_ITEMS_COUNTED so a claim can't inflate confidence by spamming
    queries), and a scaled boost from the magnitude of an observed error-rate
    delta, when known. Always clamped to [0.0, 1.0].
    """
    confidence = llm_confidence

    if deployment_marker_present:
        confidence += DEPLOYMENT_MARKER_CONFIDENCE_BOOST

    counted_items = min(len(evidence), MAX_EVIDENCE_ITEMS_COUNTED)
    confidence += counted_items * PER_EVIDENCE_ITEM_BOOST

    if error_rate_delta is not None:
        confidence += min(max(error_rate_delta, 0.0), 1.0) * ERROR_RATE_DELTA_BOOST_SCALE

    return max(0.0, min(MAX_RECALIBRATED_CONFIDENCE, confidence))


def build_evidence_link(evidence_type: str, ref: str, time_range: str) -> str:
    """Build a resolvable SigNoz UI deep link for one piece of evidence.

    Reads SIGNOZ_URL from the environment (the same var app/signoz_mcp.py passes to
    the MCP server subprocess). `ref` is the type-specific identifier: a trace ID
    for "trace", a service/query string for "log" or "metric", or a version string
    for "deployment". Path shapes follow SigNoz's documented UI URL conventions but
    have not been live-verified against a running instance in this environment -
    scripts/check_evidence_links.py is the human-verification companion that
    confirms these actually resolve once a live SigNoz stack exists (LAW1-05).
    """
    # Default is 8080, the port SigNoz's Foundry deployment actually serves on.
    # This was 3301 (SigNoz's older default) until 2026-07-25, which silently
    # produced dead evidence links on every claim whenever SIGNOZ_URL was unset -
    # exactly the failure LAW1-05's link checker exists to catch.
    base = os.getenv("SIGNOZ_URL", "http://localhost:8080").rstrip("/")

    if evidence_type == "trace":
        return f"{base}/trace/{ref}"
    if evidence_type == "log":
        return f"{base}/logs/logs-explorer?q={ref}&timeRange={time_range}"
    if evidence_type == "metric":
        return f"{base}/metrics-explorer?q={ref}&timeRange={time_range}"
    if evidence_type == "deployment":
        return f"{base}/deployments?version={ref}"
    raise ValueError(f"unknown evidence type {evidence_type!r}")
