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

import logging

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import embed_text
from app.models import Document
from app.observability import (
    RAG_PROMPT_DOC_COUNT,
    RAG_RETRIEVAL_DOC_COUNT,
    RAG_RETRIEVAL_TOP_K,
)

logger = logging.getLogger(__name__)

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


async def retrieve(session: AsyncSession, query: str, top_k: int = 3) -> list[Document]:
    """Embed `query` and return the top_k nearest Document rows by cosine distance.

    D-03: fixed top_k=3 default, no chunking, no similarity-threshold
    refusal branch. Opens the rag.retrieval span (one of the three D-07
    spans), layered on top of the free SQLAlchemyInstrumentor DB span
    underneath (per app/db.py's setup_db_instrumentation()).
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.retrieval") as span:
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
        if docs:
            context = "\n\n".join(f"# {doc.title}\n{doc.body}" for doc in docs)
        else:
            context = "(no relevant context docs were found for this question)"

        user_prompt = f"Question: {query}\n\nContext:\n{context}"

        span.set_attribute(RAG_PROMPT_DOC_COUNT, len(docs))

    logger.info("prompt construction complete")
    return SYSTEM_PROMPT, user_prompt
