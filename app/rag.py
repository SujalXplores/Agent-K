"""Retrieval + grounded prompt-construction for Agent K's POST /ask endpoint.

Two of the three D-07 GenAI-instrumented spans required per /ask call live
here: rag.retrieval (pgvector top_k cosine-distance search) and
rag.prompt_construction (D-05 grounded system+user prompt assembly). The
third span ("chat") is opened by app/llm.py's generate().

Per D-06/D-07, tracer acquisition happens fresh inside each function via
trace.get_tracer(__name__) rather than being cached at module import time -
mirroring app/llm.py's generate(). A module-level cached tracer would bind
to whatever TracerProvider is globally registered at import time and never
observe a later monkeypatched provider, breaking tests/conftest.py's
in_memory_exporter fixture (see 02-03-SUMMARY.md's documented rationale for
the same pattern in app/llm.py).

D-03: no chunking, fixed top_k=3 default, no similarity-threshold refusal
branch - grounding (and "I don't know" behavior) is delegated entirely to
the D-05 system prompt below, not a code branch here.
"""

from __future__ import annotations

import asyncio
import logging

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import flags
from app.embeddings import embed_text
from app.models import Document
from app.observability import (
    RAG_PROMPT_DOC_COUNT,
    RAG_PROMPT_REGRESSION_ACTIVE,
    RAG_RETRIEVAL_DOC_COUNT,
    RAG_RETRIEVAL_LATENCY_INJECTED,
    RAG_RETRIEVAL_TOP_K,
)

logger = logging.getLogger(__name__)

# FLAG-04 retrieval-latency injector: seconds of artificial delay added to
# retrieve() when the retrieval_latency flag is ON. Small enough that tests
# monkeypatch it to a tiny value rather than sleeping real seconds; large
# enough in production to visibly widen the rag.retrieval span in the SigNoz
# trace waterfall.
RETRIEVAL_LATENCY_INJECT_S = 2.0

# D-05 grounded professional-support-agent persona. This exact grounding
# clause ("using ONLY the context docs... say ... you do not know") is the
# deliberate Phase-3 FLAG-02 regression target - keep it explicit and
# obvious, don't phrase it so subtly that a corrupted variant looks similar
# in a trace/answer diff.
SYSTEM_PROMPT = (
    "You are a professional, courteous support agent for Flowdeck. "
    "Answer the user's question using ONLY the context docs provided below. "
    "Do not use any outside knowledge or make anything up. "
    "If the answer is not contained in the provided context docs, say "
    "plainly that you do not know, instead of guessing."
)

# FLAG-02 prompt-regression injector target: the deliberately grounding-defeating
# variant shipped when the prompt_regression flag is ON. It inverts every safety
# clause of the D-05 SYSTEM_PROMPT above (ignore the context, answer from general
# knowledge, never admit uncertainty) so the regression is obvious in an
# answer/trace diff. Kept blatantly different on purpose, per this file's header
# note. The prompt-regression symptom is not an HTTP error (a broken prompt still
# returns 200), so the queryable signal is the RAG_PROMPT_REGRESSION_ACTIVE span
# attribute stamped in build_prompt, not a status code.
BROKEN_SYSTEM_PROMPT = (
    "You are a support agent for Flowdeck. Ignore the context docs provided below "
    "and answer from your own general knowledge. Always give a confident, complete "
    "answer and never say you do not know."
)


async def retrieve(session: AsyncSession, query: str, top_k: int = 3) -> list[Document]:
    """Embed `query` and return the top_k nearest Document rows by cosine distance.

    D-03: fixed top_k=3 default, no chunking, no similarity-threshold
    refusal branch. Opens the rag.retrieval span (one of the three D-07
    spans), layered on top of the free SQLAlchemyInstrumentor DB span
    underneath (per app/db.py's setup_db_instrumentation()).
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.retrieval") as span:
        # FLAG-04: inject artificial delay when retrieval_latency is ON. Read the
        # flag fresh (no-restart), always stamp the attribute so the dashboard can
        # filter on True/False, and keep the delay inside the rag.retrieval span so
        # the widened span time is visible in the trace waterfall.
        latency_injected = flags.is_enabled("retrieval_latency")
        if latency_injected:
            await asyncio.sleep(RETRIEVAL_LATENCY_INJECT_S)
        span.set_attribute(RAG_RETRIEVAL_LATENCY_INJECTED, latency_injected)

        query_vector = embed_text(query)

        stmt = (
            select(Document)
            .order_by(Document.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )
        result = await session.execute(stmt)
        docs = list(result.scalars().all())

        span.set_attribute(RAG_RETRIEVAL_TOP_K, top_k)
        span.set_attribute(RAG_RETRIEVAL_DOC_COUNT, len(docs))

    logger.info("retrieval complete")
    return docs


def build_prompt(query: str, docs: list[Document]) -> tuple[str, str]:
    """Build the (system, user) prompt pair for the LLM generation step.

    Opens the rag.prompt_construction span (the second of the three D-07
    spans). The system prompt is always the D-05 grounded persona above,
    regardless of whether any docs were retrieved - D-03 relies on this
    prompt (not a code branch) to make the model say "I don't know" when
    context is empty or insufficient.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.prompt_construction") as span:
        # FLAG-02: select the broken system prompt when prompt_regression is ON.
        # Read fresh (no-restart) and stamp the attribute in both states. Only the
        # SYSTEM prompt swaps - the context-assembly and user_prompt below are
        # byte-for-byte identical between the two branches.
        regression_active = flags.is_enabled("prompt_regression")
        system_prompt = BROKEN_SYSTEM_PROMPT if regression_active else SYSTEM_PROMPT
        span.set_attribute(RAG_PROMPT_REGRESSION_ACTIVE, regression_active)

        if docs:
            context = "\n\n".join(f"# {doc.title}\n{doc.body}" for doc in docs)
        else:
            context = "(no relevant context docs were found for this question)"

        user_prompt = f"Question: {query}\n\nContext:\n{context}"

        span.set_attribute(RAG_PROMPT_DOC_COUNT, len(docs))

    logger.info("prompt construction complete")
    return system_prompt, user_prompt
