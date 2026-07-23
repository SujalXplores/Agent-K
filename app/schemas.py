"""Pydantic request/response models for POST /ask (D-04 contract).

AskRequest bounds untrusted question input (T-02-INPUT / T-02-DoS - a
min/max length gate) before it ever reaches retrieval or the LLM prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Incoming POST /ask request body."""

    question: str = Field(..., min_length=1, max_length=2000)


class Source(BaseModel):
    """A single retrieved-doc reference surfaced to the caller (D-04)."""

    doc_id: str
    title: str


class AskResponse(BaseModel):
    """POST /ask response body - {answer, sources} per D-04."""

    answer: str
    sources: list[Source]
