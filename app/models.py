"""SQLAlchemy models for Agent K's RAG datastore.

Single-datastore design (Postgres + pgvector) per the locked stack
decision - no separate vector DB. The embedding column width is always
derived from app.embeddings.EMBEDDING_DIM, never hardcoded a second
time here, so app/embeddings.py stays the single source of truth for
the vector dimension across models.py and the Alembic migration.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.embeddings import EMBEDDING_DIM


class Base(DeclarativeBase):
    pass


class Document(Base):
    """A single support doc, embedded whole (no chunking, per D-03)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
