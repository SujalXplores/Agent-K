"""create documents table

Revision ID: 0001
Revises:
Create Date: 2026-07-23

Creates the vector extension FIRST, then the documents table with a
vector(384) embedding column (384 = app.embeddings.EMBEDDING_DIM,
single source of truth for the dimension). This migration is the
BLOCKING gate for Task 3 - applying it to the live rag-postgres
database is what actually proves the pgvector schema exists, not just
that these Python files import cleanly.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_id", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("documents")
