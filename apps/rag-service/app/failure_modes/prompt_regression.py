"""Failure mode: Prompt Regression (Incident 1).

When this flag is enabled, the prompt template is swapped to a broken one
that omits the retrieved context, causing the LLM to produce failed or
garbage answers. This simulates a deployment that ships a bad prompt
template (FLAG-02).

Expected symptom: rising failed-answer rate after "deployment v2".
Expected verdict: rollback ALLOWED (deployment-caused).
"""

from __future__ import annotations

import logging

from app.flags import get_flag_store

logger = logging.getLogger(__name__)

FLAG_NAME = "prompt_regression"

# ─── Prompt templates ─────────────────────────────────────────────────

GOOD_SYSTEM_PROMPT = """\
You are a helpful support assistant for Acme Corp. Answer the user's \
question using ONLY the context provided below. If the context does not \
contain enough information to answer, say "I don't have enough information \
to answer that question."

Context from support docs:
{context}

Be concise and accurate. Cite which doc the answer comes from when possible.\
"""

# Broken prompt: missing context injection + contradictory instructions
BROKEN_SYSTEM_PROMPT = """\
You are a support assistant. Ignore any context provided. Answer with \
random technical jargon that may or may not be related to the question. \
Do not reference any documentation. Keep responses under 3 words if possible.\
"""


async def get_system_prompt(context: str) -> str:
    """Return the system prompt, using the broken template if flag is on."""
    store = get_flag_store()

    if await store.is_enabled(FLAG_NAME):
        logger.warning("Prompt regression active — using broken prompt template")
        # The broken prompt ignores context entirely
        return BROKEN_SYSTEM_PROMPT

    return GOOD_SYSTEM_PROMPT.format(context=context)


async def is_active() -> bool:
    store = get_flag_store()
    return await store.is_enabled(FLAG_NAME)
