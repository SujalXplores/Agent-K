"""Local sentence-transformers embedding helper for Agent K's RAG service.

Produces normalized 384-dim embedding vectors entirely locally - no
external embedding API call is ever made (RAG-02). This module is the
single source of truth for the embedding dimension: app/models.py's
Document.embedding column and the 0001_create_documents Alembic
migration MUST both derive their vector width from EMBEDDING_DIM below
rather than hardcoding 384 a second time.

Mirrors app/telemetry.py's module shape: a DEFAULT_* constant + a
lazily-initialized singleton, configured via load_dotenv() + os.getenv().
"""

import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Return the lazily-instantiated module-singleton SentenceTransformer.

    Model name is resolved from the EMBEDDING_MODEL env var (falling back
    to DEFAULT_EMBEDDING_MODEL) so swapping to an alternate 384-dim model
    (e.g. BAAI/bge-small-en-v1.5) is a one-line env change, no code change.
    """
    global _model
    if _model is None:
        load_dotenv()
        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        _model = SentenceTransformer(model_name)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single string into a normalized EMBEDDING_DIM-length vector.

    Embeddings are normalized so cosine distance is meaningful for the
    pgvector similarity search used by retrieval in Phase 2 Plan 4.
    """
    vector = get_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of strings into normalized EMBEDDING_DIM vectors."""
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()
