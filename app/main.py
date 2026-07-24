"""Agent K's monitored FastAPI RAG service.

Wires retrieval -> prompt construction -> LLM generation into the
support-answering endpoint (RAG-01/RAG-03). New routes must be registered
before OTel instrumentation is wired up further down this file - anything
added after that point is never wrapped in spans (RESEARCH.md Pattern 2 /
anti-pattern warning).
"""

import logging

import fastapi
from fastapi import Depends
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm as llm_module
from app import rag as rag_module
from app.db import get_session, setup_db_instrumentation
from app.schemas import AskRequest, AskResponse, Source
from app.telemetry import setup_telemetry

# 1. Create the app.
app = fastapi.FastAPI()


# 2. Register routes (/healthz from Phase 1, /ask added in Phase 2 - D-05).
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


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, session: AsyncSession = Depends(get_session)) -> AskResponse:
    """Retrieve -> build_prompt -> generate (RAG-01), returning {answer, sources} (D-04).

    Three GenAI-instrumented spans are emitted per call (RAG-03/D-07):
    rag.retrieval and rag.prompt_construction from app.rag, and chat from
    app.llm.generate(). Never logs the question/prompt/answer text itself
    (T-02-KEY) - only lifecycle markers, matching app/llm.py's discipline.
    """
    logging.getLogger(__name__).info("ask request received")

    docs = await rag_module.retrieve(session, req.question, top_k=3)
    system, user = rag_module.build_prompt(req.question, docs)
    result = llm_module.generate(user, system=system)

    logging.getLogger(__name__).info("answer generated")

    return AskResponse(
        answer=result.answer,
        sources=[Source(doc_id=doc.doc_id, title=doc.title) for doc in docs],
    )


# 3. Wire OTel providers (console + OTLP-HTTP dual exporters, D-06/D-07).
setup_telemetry()

# 4. Instrument the app AFTER routes are registered.
FastAPIInstrumentor.instrument_app(app)

# 5. Instrument the sync core beneath the async engine so every retrieval
#    query emits a free DB span underneath the hand-written rag.retrieval
#    span (D-07). Without this call SQLAlchemyInstrumentor never activates
#    and the free DB span is silently absent (02-VERIFICATION.md gap 3).
setup_db_instrumentation()

# 6. Correlate stdlib logging records with active trace/span context.
LoggingInstrumentor().instrument(set_logging_format=True)

logging.getLogger(__name__).info("agent-k-rag-service telemetry skeleton started")
