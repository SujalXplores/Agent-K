"""Shared GenAI telemetry helper - single source of truth for span attributes.

record_llm_call_attributes(span, request, response) is the ONE place any
gen_ai.* / agentk.* / rag.* attribute name is defined (D-06). It is deliberately
generic - it only SETS attributes on a span handed to it; it never creates a
TracerProvider or a span itself. app/llm.py calls it from generate()'s "chat"
span, app/rag.py (Phase 2 plan 02-04) calls it from the retrieval span for the
rag.retrieval.* constants, and Phase 5's Agent K self-telemetry is expected to
import and call this same function unchanged with its own request/response
shapes.

Per D-06, this module uses ONLY the stable/default gen_ai.* semantic-convention
attribute names (opentelemetry-api 1.44.0 pins) - it does NOT opt into
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental.

Content-safety note (T-02-KEY): this helper never sets an attribute equal to
raw prompt/completion text or an API key - only model names, token counts, and
a provider/cost estimate. Setting message content as a span attribute would
risk leaking user input and inflating span size.
"""

from __future__ import annotations

from typing import Any

from opentelemetry.trace import Span

# --- rag.* custom attribute-name constants (consumed by app/rag.py, 02-04) ---
RAG_RETRIEVAL_TOP_K = "rag.retrieval.top_k"
RAG_RETRIEVAL_DOC_COUNT = "rag.retrieval.doc_count"
RAG_PROMPT_DOC_COUNT = "rag.prompt_construction.doc_count"

# --- gen_ai.* stable semantic-convention attribute-name constants ---
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

# --- agentk.* custom attribute-name constants (not covered by stable semconv) ---
AGENTK_LLM_PROVIDER = "agentk.llm.provider"
AGENTK_LLM_ESTIMATED_COST_USD = "agentk.llm.estimated_cost_usd"

# --- fault-injection + deployment-marker attribute-name constants (Phase 3) ---
# Single source of truth (D-06) for every attribute the four seeded failure
# scenarios and the FLAG-06 deployment marker stamp on spans. Downstream
# injector modules (app/rag.py, app/llm.py, app/db.py, app/flags.py) import
# these constants and never define the attribute strings inline, so the
# Phase 3/7 dashboard queries that filter on them cannot silently drift.
RAG_PROMPT_REGRESSION_ACTIVE = "rag.prompt_construction.regression_active"  # FLAG-02 (app/rag.py)
RAG_RETRIEVAL_LATENCY_INJECTED = "rag.retrieval.latency_injected"  # FLAG-04 (app/rag.py)
AGENTK_LLM_RETRY_COUNT = "agentk.llm.retry_count"  # FLAG-03 (app/llm.py)
AGENTK_DB_POOL_EXHAUSTED = "agentk.db.pool_exhausted"  # FLAG-05 (app/db.py)
DEPLOYMENT_MARKER_SCENARIO = "deployment.scenario"  # FLAG-06 (app/flags.py)
DEPLOYMENT_MARKER_VERSION = "deployment.version"  # FLAG-06 (app/flags.py)

# --- SigNoz MCP query attribute-name constants (Phase 4) ---
# Stamped by app/signoz_mcp.py's single query_signoz() call site (MCP-02) on every
# "signoz_mcp.query" span, regardless of outcome, so Phase 5's investigation loop
# can read them back for loop/repeated-query detection (LAW3-02) without needing
# any MCP-specific knowledge itself.
AGENTK_MCP_TOOL_NAME = "agentk.mcp.tool_name"
AGENTK_MCP_QUERY_HASH = "agentk.mcp.query_hash"

# --- Investigation self-telemetry attribute-name constants (Phase 5, Law 3) ---
# Stamped by app/investigation.py's run_investigation() on the "agentk.investigation"
# span (LAW3-02/03) and by its child "agentk.hypothesis"/"agentk.watchdog.*" spans.
AGENTK_INVESTIGATION_ID = "agentk.investigation.id"
AGENTK_INVESTIGATION_STATE = "agentk.investigation.state"
AGENTK_INVESTIGATION_INCOMPLETE = "agentk.investigation.incomplete"
AGENTK_INVESTIGATION_DURATION_S = "agentk.investigation.duration_s"
AGENTK_INVESTIGATION_MCP_QUERY_COUNT = "agentk.investigation.mcp_query_count"
AGENTK_INVESTIGATION_MCP_QUERY_FAILURES = "agentk.investigation.mcp_query_failures"
AGENTK_INVESTIGATION_REPEATED_QUERY_COUNT = "agentk.investigation.repeated_query_count"
AGENTK_INVESTIGATION_HYPOTHESIS_COUNT = "agentk.investigation.hypothesis_count"
AGENTK_INVESTIGATION_TOTAL_TOKENS = "agentk.investigation.total_tokens"
AGENTK_HYPOTHESIS_CONFIDENCE = "agentk.hypothesis.confidence"
AGENTK_HYPOTHESIS_LLM_CONFIDENCE = "agentk.hypothesis.llm_confidence"
AGENTK_WATCHDOG_KIND = "agentk.watchdog.kind"  # "loop_breaker" | "cost_budget"
AGENTK_WATCHDOG_QUERY_HASH = "agentk.watchdog.query_hash"
AGENTK_WATCHDOG_REPEAT_COUNT = "agentk.watchdog.repeat_count"
AGENTK_WATCHDOG_TOTAL_TOKENS = "agentk.watchdog.total_tokens"
AGENTK_WATCHDOG_BUDGET = "agentk.watchdog.budget"

# --- Law 2 policy-gate attribute-name constants (Phase 6) ---
# Stamped by app/policy.py's evaluate_policy() on the "agentk.policy.decision"
# span (LAW2-06). The requirement enumerates exactly what must be recorded -
# requested action, incident ID, SLO value, threshold, confidence, allowlist
# result, cooldown result, final verdict, reason - so every one of those has a
# constant here and none is set inline at the call site. The per-check *_PASSED
# attributes make each individual gate independently queryable in the Phase 7
# Action Audit Trail dashboard, so a denied verdict shows WHICH check denied it.
AGENTK_POLICY_ACTION = "agentk.policy.action"
AGENTK_POLICY_INCIDENT_ID = "agentk.policy.incident_id"
AGENTK_POLICY_SLO_VALUE = "agentk.policy.slo_value"
AGENTK_POLICY_SLO_THRESHOLD = "agentk.policy.slo_threshold"
AGENTK_POLICY_CONFIDENCE = "agentk.policy.confidence"
AGENTK_POLICY_CONFIDENCE_THRESHOLD = "agentk.policy.confidence_threshold"
AGENTK_POLICY_SLO_PASSED = "agentk.policy.slo_passed"
AGENTK_POLICY_ALLOWLIST_PASSED = "agentk.policy.allowlist_passed"
AGENTK_POLICY_COOLDOWN_PASSED = "agentk.policy.cooldown_passed"
AGENTK_POLICY_CONFIDENCE_PASSED = "agentk.policy.confidence_passed"
AGENTK_POLICY_DEPLOYMENT_RELATED_PASSED = "agentk.policy.deployment_related_passed"
AGENTK_POLICY_SANDBOX_PASSED = "agentk.policy.sandbox_passed"
AGENTK_POLICY_VERDICT = "agentk.policy.verdict"  # "approved" | "denied"
AGENTK_POLICY_REASON = "agentk.policy.reason"
AGENTK_POLICY_FAILED_CHECKS = "agentk.policy.failed_checks"  # comma-joined check names

# --- Law 2 action-execution attribute-name constants (Phase 6) ---
# Stamped by app/rollback.py on the "agentk.action.rollback" span - the record of
# what Agent K actually DID after an approved verdict, and whether SigNoz
# independently confirmed recovery afterwards (LAW2-04).
AGENTK_ACTION_KIND = "agentk.action.kind"
AGENTK_ACTION_STATUS = "agentk.action.status"  # "executed" | "failed" | "conflict"
AGENTK_ACTION_HTTP_STATUS = "agentk.action.http_status"
AGENTK_ACTION_PREVIOUS_IMAGE = "agentk.action.previous_image"  # sidecar-reported pre-mutation tag
AGENTK_ACTION_VERIFIED = "agentk.action.verified"
AGENTK_ACTION_VERIFICATION_DETAIL = "agentk.action.verification_detail"

# Best-effort, zero-budget-friendly per-1K-token rate used only to produce a
# non-zero estimated_cost_usd attribute for Law 3 reuse (Phase 5). Free-tier
# providers (Groq/Cerebras/Gemini Flash) have effectively $0 real cost during
# the hackathon; this constant exists so the attribute is present and
# non-negative, not to be a billing-accurate figure.
_ESTIMATED_RATE_USD_PER_1K_TOKENS = 0.0


def _get(obj: Any, name: str) -> Any:
    """Defensively read an attribute from either an object or a dict/mapping.

    Supports both OpenAI SDK response/request objects (attribute access) and
    plain dicts/namespaces (Phase 5 may pass its own shapes), tolerating a
    missing or None value without raising.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def record_llm_call_attributes(span: Span, request: Any, response: Any) -> None:
    """Set stable gen_ai.* + custom agentk.* attributes on an active LLM span.

    Args:
        span: an active OTel span (e.g. the "chat" span opened by
            app/llm.py's generate()). This function never creates a span.
        request: an object or dict describing the outbound request - only
            `.model` is read.
        response: an object or dict describing the completion result - reads
            `.model` and `.usage.input_tokens` / `.usage.output_tokens`.
            `.usage` may be None or absent; this is tolerated.

    Never sets: raw prompt text, raw completion text, or any API key.
    """
    request_model = _get(request, "model")
    response_model = _get(response, "model")
    # `provider` is not part of the OpenAI SDK's request/response shapes, so it
    # is read defensively and falls back to "openai" (the SDK family all three
    # locked providers are accessed through) when the caller doesn't attach
    # one. app/llm.py's generate() passes a request object carrying the actual
    # provider name (groq/cerebras/gemini) so real spans reflect D-08 exactly.
    provider = _get(request, "provider") or _get(response, "provider") or "openai"

    span.set_attribute(GEN_AI_SYSTEM, provider)
    span.set_attribute(AGENTK_LLM_PROVIDER, provider)
    span.set_attribute(GEN_AI_OPERATION_NAME, "chat")

    if request_model is not None:
        span.set_attribute(GEN_AI_REQUEST_MODEL, request_model)
    if response_model is not None:
        span.set_attribute(GEN_AI_RESPONSE_MODEL, response_model)

    usage = _get(response, "usage")
    input_tokens = _get(usage, "input_tokens")
    output_tokens = _get(usage, "output_tokens")

    if input_tokens is not None:
        span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
    if output_tokens is not None:
        span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)

    total_tokens = (input_tokens or 0) + (output_tokens or 0)
    estimated_cost = (total_tokens / 1000.0) * _ESTIMATED_RATE_USD_PER_1K_TOKENS
    span.set_attribute(AGENTK_LLM_ESTIMATED_COST_USD, estimated_cost)
