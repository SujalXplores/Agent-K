"""Diagnostic: send a test span via OTLP to SigNoz and print any errors.

Uses SimpleSpanProcessor (synchronous, no batching) so errors are visible.
Run: python scripts/test_otlp.py
"""

from __future__ import annotations

import sys

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

ENDPOINT = "http://localhost:4318/v1/traces"
SERVICE_NAME = "rag-support-service-test"


def main() -> None:
    print(f"OTLP endpoint: {ENDPOINT}")
    print("Creating tracer provider with SimpleSpanProcessor (synchronous)...")

    resource = Resource.create(
        {"service.name": SERVICE_NAME, "service.version": "test"}
    )
    provider = TracerProvider(resource=resource)

    # SimpleSpanProcessor exports synchronously — errors are raised immediately
    exporter = OTLPSpanExporter(endpoint=ENDPOINT)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer(__name__)

    print("Creating and ending a test span...")
    with tracer.start_as_current_span("test.otlp.diagnostic") as span:
        span.set_attribute("test.diagnostic", True)
        span.set_attribute("test.timestamp", "2026-07-23")

    print("Span ended. SimpleSpanProcessor should have exported it synchronously.")

    # Force flush just in case
    result = provider.force_flush(timeout_millis=10000)
    print(f"force_flush result: {result}")

    if result:
        print("\nSUCCESS: Span was exported without error.")
        print(f"Check http://localhost:8080 for service '{SERVICE_NAME}'")
    else:
        print("\nFAILED: Export did not complete within timeout.")
        sys.exit(1)


if __name__ == "__main__":
    main()
