"""OpenTelemetry SDK bootstrap for the RAG support service.

Configures traces, metrics, and logs with a console exporter (default) or
OTLP exporter (when SigNoz is available). Also provides the shared
``genai_span_attrs`` helper that centralizes GenAI semantic-convention
attribute names — per PITFALLS.md Pitfall 3, this is the single source of
truth to avoid attribute-name drift between call sites.

Usage::

    from app.otel import tracer, genai_span_attrs
    with tracer.start_as_current_span("my.operation") as span:
        span.set_attributes(genai_span_attrs(model="llama-3.1", ...))
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False
_tracer: trace.Tracer | None = None
_meter: metrics.Meter | None = None


def _build_resource() -> Resource:
    settings = get_settings()
    return Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
            "deployment.environment": "development",
        }
    )


def _setup_tracing(resource: Resource) -> trace.Tracer:
    settings = get_settings()
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter == "otlp":
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces"
                )
            )
        )
    else:
        # Console exporter — always available for debugging
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


def _setup_metrics(resource: Resource) -> metrics.Meter:
    settings = get_settings()

    if settings.otel_exporter == "otlp":
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/metrics"
            )
        )
    else:
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter())

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(__name__)


def _setup_logging(resource: Resource) -> None:
    settings = get_settings()
    provider = LoggerProvider(resource=resource)

    if settings.otel_exporter == "otlp":
        provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/logs"
                )
            )
        )
    # Console logging is handled by Python's logging module directly;
    # OTLP log export is only needed when sending to SigNoz.

    set_logger_provider(provider)

    handler = LoggingHandler(logger_provider=provider)
    handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)


def init_otel() -> None:
    """Initialize OpenTelemetry SDK. Safe to call once at startup."""
    global _initialized, _tracer, _meter

    if _initialized:
        return

    resource = _build_resource()
    _tracer = _setup_tracing(resource)
    _meter = _setup_metrics(resource)
    _setup_logging(resource)

    _initialized = True
    logger.info(
        "OpenTelemetry initialized (exporter=%s, service=%s)",
        get_settings().otel_exporter,
        get_settings().otel_service_name,
    )


def get_tracer() -> trace.Tracer:
    """Return the configured tracer. Call ``init_otel`` first."""
    if _tracer is None:
        init_otel()
    assert _tracer is not None
    return _tracer


def get_meter() -> metrics.Meter:
    """Return the configured meter. Call ``init_otel`` first."""
    if _meter is None:
        init_otel()
    assert _meter is not None
    return _meter


# ─── GenAI semantic-convention attribute helper ──────────────────────
# Per PITFALLS.md Pitfall 3: centralize attribute names here so they
# don't drift between the RAG app and (later) Agent K's self-telemetry.
# Attribute names sourced from the OTel GenAI semconv registry:
# https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/


def genai_span_attrs(
    *,
    model: str | None = None,
    operation: str | None = None,
    provider: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    finish_reasons: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a dict of ``gen_ai.*`` span attributes.

    Only non-None values are included. Additional custom attributes can be
    passed via ``**extra`` and will be prefixed with ``gen_ai.`` if not
    already namespaced.
    """
    attrs: dict[str, Any] = {}

    if model is not None:
        attrs["gen_ai.request.model"] = model
    if operation is not None:
        attrs["gen_ai.operation.name"] = operation
    if provider is not None:
        attrs["gen_ai.provider.name"] = provider
    if input_tokens is not None:
        attrs["gen_ai.usage.input_tokens"] = input_tokens
    if output_tokens is not None:
        attrs["gen_ai.usage.output_tokens"] = output_tokens
    if finish_reasons is not None:
        attrs["gen_ai.response.finish_reasons"] = finish_reasons

    for key, value in extra.items():
        full_key = key if key.startswith("gen_ai.") else f"gen_ai.{key}"
        attrs[full_key] = value

    return attrs
