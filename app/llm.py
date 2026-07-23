"""Single OpenAI-compatible LLM client module (RAG-04).

get_client() is the ONLY place an openai.OpenAI client is constructed in this
codebase. Switching between Groq / Cerebras / Gemini Flash happens purely via
the LLM_PROVIDER env var (D-08, default "groq") - no code change, no separate
provider SDK. Per CLAUDE.md's "What NOT to Use": no LiteLLM proxy, no
provider-specific SDKs (groq/cerebras-cloud-sdk/google-genai) as the client.

generate() wraps the completion call in a single "chat" span (the third of
the three D-07 spans - retrieval, prompt-construction, generation) and
delegates all gen_ai.*/agentk.* attribute-setting to the shared
record_llm_call_attributes() helper in app/observability.py (D-06), so this
module never re-defines an attribute name.

Provider errors are intentionally NOT caught here - they propagate so the
/ask handler (02-04) can surface them; retry logic is explicitly out of scope
for this phase (T-02-05, Phase 3's injected retry-storm scenario).
"""

from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from typing import NamedTuple

from dotenv import load_dotenv
from openai import OpenAI
from opentelemetry import trace

from app.observability import record_llm_call_attributes

logger = logging.getLogger(__name__)

# CLAUDE.md's locked provider table (D-08). Do NOT re-derive base_urls - groq's
# model is the locked default; cerebras/gemini model ids are the D-08
# alternates per their respective OpenAI-compat docs.
PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "model": "llama3.1-8b",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
}


class LlmResult(NamedTuple):
    """Result of a single generate() call."""

    answer: str
    model: str
    provider: str
    input_tokens: int | None
    output_tokens: int | None


def _resolve_provider() -> tuple[str, dict[str, str]]:
    """Read LLM_PROVIDER (default "groq") and look up its config.

    Raises KeyError immediately for an unrecognized provider (T-02-04) rather
    than silently falling back or mis-routing to a default.
    """
    provider = os.getenv("LLM_PROVIDER", "groq")
    try:
        cfg = PROVIDER_CONFIG[provider]
    except KeyError as exc:
        raise KeyError(
            f"Unknown LLM_PROVIDER={provider!r}; must be one of "
            f"{sorted(PROVIDER_CONFIG)}"
        ) from exc
    return provider, cfg


def get_client() -> OpenAI:
    """Build the single OpenAI-compatible client for the active provider.

    This is the ONLY function in the codebase that constructs an
    openai.OpenAI client (RAG-04) - base_url/api_key are swapped purely by
    reading LLM_PROVIDER / {PROVIDER}_API_KEY env vars.
    """
    load_dotenv()
    provider, cfg = _resolve_provider()
    return OpenAI(base_url=cfg["base_url"], api_key=os.getenv(f"{provider.upper()}_API_KEY"))


def generate(prompt: str, system: str | None = None) -> LlmResult:
    """Generate a chat completion, wrapped in one gen_ai "chat" span.

    Args:
        prompt: the user message content.
        system: optional system-prompt content (D-05's grounding persona is
            passed here by the /ask handler in 02-04).

    Returns:
        An LlmResult with the assistant's answer text and token usage.
    """
    load_dotenv()
    provider, cfg = _resolve_provider()
    client = get_client()

    messages: list[dict[str, str]] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("chat") as span:
        response = client.chat.completions.create(model=cfg["model"], messages=messages)

        # Real OpenAI-SDK completions expose usage.prompt_tokens/
        # completion_tokens (see openai.types.completion_usage), while the
        # gen_ai.* stable semconv (and this project's shared helper) name
        # them input_tokens/output_tokens. Normalize here - once, at the
        # single call site - so record_llm_call_attributes only ever needs
        # to understand one attribute-name shape regardless of whether the
        # caller is a real provider response or a test double that already
        # uses input_tokens/output_tokens directly.
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
        if input_tokens is None and usage is not None:
            input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
        if output_tokens is None and usage is not None:
            output_tokens = getattr(usage, "completion_tokens", None)

        request_like = SimpleNamespace(model=cfg["model"], provider=provider)
        response_like = SimpleNamespace(
            model=getattr(response, "model", cfg["model"]),
            usage=(
                SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
                if usage is not None
                else None
            ),
        )
        record_llm_call_attributes(span, request_like, response_like)

        answer = response.choices[0].message.content

    logger.info("llm generation complete")

    return LlmResult(
        answer=answer,
        model=getattr(response, "model", cfg["model"]),
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
