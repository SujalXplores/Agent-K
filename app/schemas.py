"""Pydantic request/response models for POST /ask (D-04 contract).

AskRequest bounds untrusted question input (T-02-INPUT / T-02-DoS - a
min/max length gate) before it ever reaches retrieval or the LLM prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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


class FlagToggleRequest(BaseModel):
    """POST /admin/flags body — toggle one failure-injection scenario (FLAG-01)."""

    name: str
    enabled: bool

    @field_validator("name")
    @classmethod
    def _known_flag(cls, value: str) -> str:
        # Import app.flags lazily inside the validator (not at module load) so
        # app.schemas has no import-time dependency on app.flags — avoids the
        # import cycle app.flags -> app.observability -> ... and keeps schemas
        # importable in isolation. An unknown flag name raises ValueError, which
        # Pydantic surfaces as a 422 at the endpoint.
        from app.flags import FLAG_NAMES

        if value not in FLAG_NAMES:
            raise ValueError(f"unknown flag name {value!r}; must be one of {list(FLAG_NAMES)}")
        return value


class FlagStateResponse(BaseModel):
    """GET/POST /admin/flags response — current state of all four flags (FLAG-01)."""

    flags: dict[str, bool]
