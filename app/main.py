"""Agent K's monitored FastAPI RAG service.

Wires retrieval -> prompt construction -> LLM generation into the
support-answering endpoint (RAG-01/RAG-03). New routes must be registered
before OTel instrumentation is wired up further down this file - anything
added after that point is never wrapped in spans (RESEARCH.md Pattern 2 /
anti-pattern warning).
"""

import logging
import os

import fastapi
from fastapi import Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from sqlalchemy.ext.asyncio import AsyncSession

from app import alerts_webhook, flags, report
from app import investigation as investigation_module
from app import llm as llm_module
from app import policy as policy_module
from app import rag as rag_module
from app.db import get_session, setup_db_instrumentation
from app.schemas import (
    AskRequest,
    AskResponse,
    FlagStateResponse,
    FlagToggleRequest,
    Source,
)
from app.telemetry import setup_telemetry

# 1. Create the app.
app = fastapi.FastAPI()

# CORS - lets a browser-hosted frontend (e.g. the Vercel landing page) call
# this API from a different origin. ALLOWED_ORIGINS is a comma-separated list;
# unset/empty means "no cross-origin JS callers allowed" rather than silently
# opening to "*", since this API is also reachable from the public internet.
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Apply any deliberately-seeded failure scenarios (AGENT_K_SEEDED_FLAGS). Empty in
# every normal deployment; set only in the v2-broken demo image so the Law 2
# rollback has a genuinely bad build to roll back FROM. Logs loudly when non-empty.
flags.seed_flags_from_env()


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


# Admin failure-injection endpoints (FLAG-01). Registered here in step 2 -
# BEFORE FastAPIInstrumentor.instrument_app below - so every toggle/audit call
# is wrapped in a request span like any other route (the same route-before-
# instrumentation rule the /ask handler depends on). POST is token-gated
# (X-Admin-Token vs ADMIN_TOKEN env; open when the env var is unset, per D-03
# local-demo decision); GET is an unauthenticated read-only state audit so an
# operator can always see and reset stuck flags.
@app.post("/admin/flags", response_model=FlagStateResponse)
async def set_flags(
    req: FlagToggleRequest,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> FlagStateResponse:
    if not flags.token_matches(x_admin_token):
        raise fastapi.HTTPException(status_code=401, detail="invalid admin token")
    flags.set_flag(req.name, req.enabled)
    # FLAG-06: emit a deployment.marker span only for deployment-class scenarios
    # toggled ON; the emitter itself enforces the asymmetry.
    flags.maybe_emit_deployment_marker(req.name, req.enabled)
    logging.getLogger(__name__).info(
        "flag toggled: %s -> %s", req.name, req.enabled
    )
    return FlagStateResponse(flags=flags.get_all())


@app.get("/admin/flags", response_model=FlagStateResponse)
async def get_flags() -> FlagStateResponse:
    return FlagStateResponse(flags=flags.get_all())


@app.post("/admin/reset")
async def reset_demo_state(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Clear every in-process demo store so a demo can re-run without a restart.

    Resets, in one call:
      * failure-injection flags (app.flags.reset_all) -> all OFF
      * persisted alerts (app.alerts_webhook.clear_alerts) -> empty
      * investigations (app.investigation.clear_investigations) -> empty
      * Law 2 cooldown ledger (app.policy.clear_cooldowns) -> empty

    Token-gated exactly like POST /admin/flags: open when ADMIN_TOKEN is unset
    (local-demo convenience), constant-time compared when set. Does NOT touch
    SigNoz, Postgres, or the deployer - only this process's in-memory state -
    so a reset is always safe and always fast (sub-millisecond).

    Returns a count per store so the caller can confirm what was cleared.
    """
    if not flags.token_matches(x_admin_token):
        raise fastapi.HTTPException(status_code=401, detail="invalid admin token")

    alert_count = len(alerts_webhook.get_alerts())
    investigation_count = len(investigation_module.list_investigations())

    flags.reset_all()
    alerts_webhook.clear_alerts()
    investigation_module.clear_investigations()
    policy_module.clear_cooldowns()

    logging.getLogger(__name__).info(
        "demo state reset: cleared %d alerts, %d investigations, all flags, all cooldowns",
        alert_count,
        investigation_count,
    )
    return {
        "reset": True,
        "cleared": {
            "alerts": alert_count,
            "investigations": investigation_count,
            "flags": "all_off",
            "cooldowns": "cleared",
        },
    }


# Inbound SigNoz alert webhook (DASH-05). Included here in step 2 - BEFORE
# FastAPIInstrumentor.instrument_app below - so POST /alerts/webhook is wrapped
# in a request span. This is the reusable entrypoint Agent K's Phase-5 loop
# consumes as its investigation trigger.
app.include_router(alerts_webhook.router)

# Human-facing incident report pages (REPT-01/02/03). Registered here in step 2 -
# BEFORE FastAPIInstrumentor.instrument_app below - for the same reason as every
# route above: anything added after instrumentation is never wrapped in a span.
app.include_router(report.router)


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
