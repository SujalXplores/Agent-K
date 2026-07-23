"""Agent K's monitored FastAPI RAG service - Phase 1 skeleton.

No /ask or RAG logic yet (D-05). Phase 2 adds real routes above the
instrumentation call without re-wiring OTel setup.

Ordering matters (RESEARCH.md Pattern 2 / anti-pattern warning):
routes must be registered BEFORE FastAPIInstrumentor.instrument_app(app)
is called, otherwise routes added earlier are never wrapped in spans.
"""

import logging

import fastapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from app.telemetry import setup_telemetry

# 1. Create the app.
app = fastapi.FastAPI()


# 2. Register routes (only /healthz in this phase - D-05).
@app.get("/healthz")
async def healthz():
    # Explicit per-request log call so this route emits a trace-correlated
    # log record (TELE-03). uvicorn's own access log is emitted via the
    # `uvicorn.access` logger, which sets `propagate: False` by default and
    # therefore never reaches the root logger's OTel LoggingHandler - it
    # prints to console but is never exported. This call runs inside the
    # active request span, so LoggingInstrumentor injects a real (non-zero)
    # trace_id/span_id into it and it is exported like any other log.
    logging.getLogger(__name__).info("healthz request handled")
    return {"status": "ok"}


# 3. Wire OTel providers (console + OTLP-HTTP dual exporters, D-06/D-07).
setup_telemetry()

# 4. Instrument the app AFTER routes are registered.
FastAPIInstrumentor.instrument_app(app)

# 5. Correlate stdlib logging records with active trace/span context.
LoggingInstrumentor().instrument(set_logging_format=True)

logging.getLogger(__name__).info("agent-k-rag-service telemetry skeleton started")
