"""Retrieval layer: Document model, corpus seeding, and vector search.

Uses pgvector's cosine distance operator (``<=>``) for similarity search.
Each retrieval is wrapped in a manual span so the retrieval step is
individually visible in telemetry — per RAG-03 requirement.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.db import Base, get_session_factory
from app.otel import get_tracer

logger = logging.getLogger(__name__)

# all-MiniLM-L6-v2 produces 384-dimensional vectors
EMBEDDING_DIM = 384


class Document(Base):
    """A support document stored with its embedding vector."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="general")
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r}>"


# ─── Embedding model (lazy-loaded singleton) ──────────────────────────

_embedding_model = None


def get_embedding_model():
    """Return the sentence-transformers model, loading it on first call."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded (dim=%d)", EMBEDDING_DIM)
    return _embedding_model


def embed_text(text: str) -> list[float]:
    """Embed a single text string into a vector."""
    model = get_embedding_model()
    return model.encode(text).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single batch (more efficient)."""
    model = get_embedding_model()
    embeddings = model.encode(texts)
    return [e.tolist() for e in embeddings]


# ─── Corpus seeding ───────────────────────────────────────────────────

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "docs"


async def seed_corpus() -> int:
    """Load and seed the synthetic support docs into the database.

    Returns the number of documents inserted.
    """
    tracer = get_tracer()

    with tracer.start_as_current_span("rag.seed_corpus") as span:
        docs = _load_corpus_files()
        span.set_attribute("rag.seed.doc_count", len(docs))

        if not docs:
            logger.warning("No corpus documents found in %s", CORPUS_DIR)
            return 0

        # Embed all documents in a batch
        texts = [f"{d['title']}\n{d['content']}" for d in docs]
        embeddings = embed_batch(texts)

        factory = get_session_factory()
        async with factory() as session:
            # Clear existing docs (idempotent re-seed)
            await session.execute(text("DELETE FROM documents"))
            await session.commit()

            for doc, emb in zip(docs, embeddings, strict=True):
                session.add(
                    Document(
                        title=doc["title"],
                        content=doc["content"],
                        category=doc.get("category", "general"),
                        embedding=emb,
                    )
                )
            await session.commit()

        logger.info("Seeded %d documents into the corpus", len(docs))
        span.set_attribute("rag.seed.inserted", len(docs))
        return len(docs)


def _load_corpus_files() -> list[dict[str, str]]:
    """Load all .md files from the corpus directory."""
    docs: list[dict[str, str]] = []

    if not CORPUS_DIR.exists():
        logger.warning("Corpus directory does not exist: %s", CORPUS_DIR)
        return docs

    for md_file in sorted(CORPUS_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        # Use the first line (minus #) as the title
        lines = content.strip().split("\n", 1)
        title = lines[0].lstrip("# ").strip() if lines else md_file.stem
        body = lines[1].strip() if len(lines) > 1 else content

        # Category from subdirectory if present, else from filename prefix
        category = md_file.stem.split("-")[0] if "-" in md_file.stem else "general"

        docs.append(
            {"title": title, "content": body, "category": category}
        )

    return docs


# ─── Retrieval ────────────────────────────────────────────────────────


async def retrieve(
    query: str,
    *,
    top_k: int = 5,
    session: AsyncSession | None = None,
    delay_seconds: float = 0.0,
) -> list[dict]:
    """Retrieve the top-k most similar documents to ``query``.

    Parameters
    ----------
    query
        The user's question.
    top_k
        Number of documents to return.
    session
        Optional existing session. If None, a new one is created.
    delay_seconds
        Artificial delay (used by the retrieval_latency failure mode).
    """
    tracer = get_tracer()

    with tracer.start_as_current_span("rag.retrieval") as span:
        span.set_attribute("rag.retrieval.query_length", len(query))
        span.set_attribute("rag.retrieval.top_k", top_k)

        # Embed the query
        query_embedding = embed_text(query)
        span.set_attribute("rag.retrieval.query_embedded", True)

        # Inject artificial delay if requested (failure mode: retrieval_latency)
        if delay_seconds > 0:
            span.set_attribute("rag.retrieval.injected_delay_s", delay_seconds)
            logger.info("Injecting %.1fs retrieval delay", delay_seconds)
            await asyncio.sleep(delay_seconds)

        # Execute the vector similarity search
        if session is None:
            factory = get_session_factory()
            async with factory() as sess:
                results = await _execute_search(sess, query_embedding, top_k)
        else:
            results = await _execute_search(session, query_embedding, top_k)

        span.set_attribute("rag.retrieval.doc_count", len(results))

        logger.info("Retrieved %d docs for query: %s", len(results), query[:80])
        return results


async def _execute_search(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int,
) -> list[dict]:
    """Execute the pgvector cosine similarity search."""
    stmt = (
        select(
            Document,
            Document.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .order_by("distance")
        .limit(top_k)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "category": doc.category,
            "distance": float(distance),
        }
        for doc, distance in rows
    ]
