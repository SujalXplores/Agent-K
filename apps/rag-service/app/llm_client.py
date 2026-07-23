"""Single OpenAI-compatible LLM client.

Per STACK.md: one ``openai.AsyncOpenAI`` instance with ``base_url`` swapped
per provider (Groq / Cerebras / Gemini Flash). Provider is selected via the
``LLM_PROVIDER`` env var — no code changes needed to switch.

All LLM calls are wrapped in an OTel span with GenAI semantic-convention
attributes via the shared ``genai_span_attrs`` helper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings
from app.otel import genai_span_attrs, get_tracer

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured result of an LLM call."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reasons: list[str]
    provider: str


# ─── Client factory ────────────────────────────────────────────────────

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Return the configured OpenAI-compatible client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        logger.info(
            "LLM client initialized (provider=%s, model=%s, base_url=%s)",
            settings.llm_provider,
            settings.llm_model,
            settings.llm_base_url,
        )
    return _client


def reset_client() -> None:
    """Reset the cached client (used when provider config changes)."""
    global _client
    _client = None


# ─── Generation ───────────────────────────────────────────────────────


async def generate_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: float | None = None,
    retries: int = 0,
) -> LLMResponse:
    """Call the LLM and return a structured response with telemetry.

    Parameters
    ----------
    messages
        OpenAI-format chat messages.
    temperature
        Sampling temperature.
    max_tokens
        Maximum tokens to generate.
    timeout
        Override the client timeout (used by retry_storm failure mode).
    retries
        Number of retry attempts on failure (used by retry_storm).
    """
    settings = get_settings()
    tracer = get_tracer()
    client = get_client()

    total_input_tokens = 0
    total_output_tokens = 0
    last_response = None
    attempt = 0
    max_attempts = 1 + retries

    with tracer.start_as_current_span(
        "rag.generation.llm_call",
        attributes=genai_span_attrs(
            model=settings.llm_model,
            operation="chat.completion",
            provider=settings.llm_provider,
        ),
    ) as span:
        span.set_attribute("rag.generation.attempts", max_attempts)
        span.set_attribute("rag.generation.temperature", temperature)
        span.set_attribute("rag.generation.max_tokens", max_tokens)

        for attempt in range(1, max_attempts + 1):
            try:
                kwargs: dict = {
                    "model": settings.llm_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if timeout is not None:
                    kwargs["timeout"] = timeout

                response = await client.chat.completions.create(**kwargs)

                usage = response.usage
                in_tok = usage.prompt_tokens if usage else 0
                out_tok = usage.completion_tokens if usage else 0
                total_input_tokens += in_tok
                total_output_tokens += out_tok

                finish_reasons = [
                    choice.finish_reason or "unknown"
                    for choice in response.choices
                ]

                last_response = LLMResponse(
                    text=response.choices[0].message.content or "",
                    model=settings.llm_model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    finish_reasons=finish_reasons,
                    provider=settings.llm_provider,
                )

                span.set_attributes(
                    genai_span_attrs(
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        finish_reasons=finish_reasons,
                    )
                )
                span.set_attribute("rag.generation.successful_attempt", attempt)
                break

            except Exception as exc:
                logger.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                span.set_attribute(
                    f"rag.generation.attempt_{attempt}_error", str(exc)[:200]
                )
                if attempt >= max_attempts:
                    span.set_attribute("rag.generation.all_attempts_failed", True)
                    raise
                # Brief pause before retry (no backoff library needed)
                import asyncio

                await asyncio.sleep(0.1 * attempt)

    assert last_response is not None
    return last_response
