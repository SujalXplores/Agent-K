"""OpenTelemetry setup for Agent K's FastAPI RAG service.

Registers dual exporters (console + OTLP-HTTP) on all three signals -
traces, metrics, logs - with no env-var toggle between them (D-06).
Console output proves span/metric/log generation independent of whether
OTLP delivery into SigNoz is actually working, which is the #1
Day-1 debugging aid this module exists to provide.

OTLP exporters are imported exclusively from the
`opentelemetry.exporter.otlp.proto.http` package family (HTTP/protobuf,
port 4318) - never the gRPC transport (D-07).

Phase 2 imports `setup_telemetry()` from this module and calls it at
startup without needing to re-wire any of the provider setup below.
"""

import os

from dotenv import load_dotenv
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

DEFAULT_OTLP_ENDPOINT = "http://localhost:4318"
DEFAULT_SERVICE_NAME = "agent-k-rag-service"


def setup_telemetry() -> None:
    """Build and register TracerProvider, MeterProvider, and LoggerProvider.

    Each provider registers both a console exporter and an OTLP-HTTP
    exporter (always on, no toggle - D-06). Call once at application
    startup, after routes are registered but before
    FastAPIInstrumentor.instrument_app(app) is called.
    """
    load_dotenv()

    otlp_base = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", DEFAULT_OTLP_ENDPOINT).rstrip("/")
    service_name = os.getenv("OTEL_SERVICE_NAME", DEFAULT_SERVICE_NAME)

    resource = Resource.create({SERVICE_NAME: service_name})

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_base}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(ConsoleMetricExporter()),
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{otlp_base}/v1/metrics")
            ),
        ],
    )
    metrics.set_meter_provider(meter_provider)

    # --- Logs ---
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(ConsoleLogExporter()))
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{otlp_base}/v1/logs"))
    )
    set_logger_provider(logger_provider)

    # A LoggingHandler is deliberately NOT attached here.
    # opentelemetry-instrumentation-logging's LoggingInstrumentor().instrument(
    # set_logging_format=True) - called in app/main.py right after this
    # function returns - auto-attaches its own LoggingHandler bound to
    # whatever LoggerProvider is globally registered (set above via
    # set_logger_provider). Attaching a second handler here would export
    # every log record twice (once per handler) through both the console
    # and OTLP processors registered above.
