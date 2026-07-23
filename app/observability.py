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
