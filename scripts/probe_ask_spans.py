"""Production span probe for POST /ask (02-VERIFICATION.md gap 2 + gap 3).

tests/conftest.py's in_memory_exporter fixture monkeypatches the tracer
provider AFTER app.main has already been imported, so FastAPI and
SQLAlchemy instrumentation - which bind their tracers at instrument time -
can never be observed from inside the normal test process. Measuring the
real production span set requires a fresh process that registers an
observable provider BEFORE app.main is imported.

Usage: python scripts/probe_ask_spans.py <output_json_path>

Writes {"http_status": int, "span_count": int, "spans": [{"name", "scope",
"status", "attributes"}]} to the given path. Attribute VALUES are never
recorded, only attribute KEYS - values can contain model names and token
counts, and this file must stay safe to commit or paste into an issue
(T-02-KEY).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Running this file directly (`python scripts/probe_ask_spans.py`) puts the
# script's own directory on sys.path, not the repo root, so `import app.*`
# would fail. Add the repo root explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _install_observable_provider():
    """Register an in-memory-exporting TracerProvider before app.main is imported."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if trace.get_tracer_provider() is not provider:
        raise RuntimeError(
            "failed to register the probe's TracerProvider as the global "
            "provider - measuring the wrong provider would silently "
            "invalidate every span this probe reports"
        )
    return exporter


def _stub_llm_provider():
    """Ensure a placeholder credential exists and stub the third-party call.

    Only the provider call is stubbed - the database and the local
    embedding model are real, so the probe genuinely exercises the
    pgvector query and therefore the DB span.
    """
    os.environ.setdefault("GROQ_API_KEY", "probe-placeholder-key")

    import app.llm as llm_module

    def _fake_openai(**kwargs):
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        model="llama-3.1-8b-instant",
                        usage=SimpleNamespace(input_tokens=7, output_tokens=13),
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content="Probe stub answer.")
                            )
                        ],
                    )
                )
            )
        )

    llm_module.OpenAI = _fake_openai


def main(output_path: str) -> None:
    exporter = _install_observable_provider()
    _stub_llm_provider()

    from fastapi.testclient import TestClient

    import app.main as main_module

    with TestClient(main_module.app) as client:
        response = client.post("/ask", json={"question": "How do I rotate an API key?"})

    spans = exporter.get_finished_spans()
    payload = {
        "http_status": response.status_code,
        "span_count": len(spans),
        "spans": [
            {
                "name": span.name,
                "scope": span.instrumentation_scope.name if span.instrumentation_scope else None,
                "status": span.status.status_code.name,
                "attributes": sorted(span.attributes.keys()) if span.attributes else [],
            }
            for span in spans
        ],
    }

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/probe_ask_spans.py <output_json_path>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
