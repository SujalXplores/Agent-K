"""Idempotent corpus seed script for Agent K's RAG datastore (RAG-02).

Reads every doc under data/corpus/ (see data/corpus/README.md for the
exact on-disk format), embeds each doc body in one local batch call via
app.embeddings.embed_texts (sentence-transformers - the ONLY embedding
path used here; no remote/network embedding API is ever called), and
upserts the results into the `documents` table idempotently, keyed on
doc_id, so re-running this script does not create duplicates or drift
the row count.

Run as: python -m scripts.seed_corpus
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import delete

from app.db import AsyncSessionLocal
from app.embeddings import embed_texts
from app.models import Document

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "data" / "corpus"

logger = logging.getLogger(__name__)


def load_corpus() -> list[dict]:
    """Read every doc under data/corpus into a list of doc dicts.

    Per data/corpus/README.md's format: one markdown file per doc at
    data/corpus/<topic>/<slug>.md. The filename slug (without .md) is
    the stable doc_id, the first line is a level-1 heading whose text
    (after stripping "# ") is the title, and everything after the
    following blank line is the body.
    """
    docs: list[dict] = []
    for path in sorted(CORPUS_ROOT.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            raise ValueError(
                f"{path} does not start with a level-1 heading ('# Title')"
            )
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()
        doc_id = path.stem
        docs.append({"doc_id": doc_id, "title": title, "body": body})
    return docs


async def seed() -> int:
    """Embed and idempotently upsert every corpus doc into `documents`.

    Idempotent via delete-all-then-insert inside a single transaction:
    re-running this function leaves the final row count and content
    identical to the prior run (no duplicates, no drift), since the
    corpus on disk is the single source of truth for what should exist
    in the table.
    """
    docs = load_corpus()
    if not docs:
        raise RuntimeError(f"No corpus docs found under {CORPUS_ROOT}")

    bodies = [doc["body"] for doc in docs]
    # Local-only embedding path (RAG-02) - app.embeddings wraps a local
    # sentence-transformers model with zero network calls.
    embeddings = embed_texts(bodies)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Idempotency: clear existing rows first, then insert the
            # current corpus fresh, all inside one transaction so a
            # failure mid-seed leaves the previous state untouched
            # rather than a half-seeded table.
            await session.execute(delete(Document))
            for doc, embedding in zip(docs, embeddings, strict=True):
                session.add(
                    Document(
                        doc_id=doc["doc_id"],
                        title=doc["title"],
                        body=doc["body"],
                        embedding=embedding,
                    )
                )

    n = len(docs)
    logger.info("corpus seeding complete: %d docs", n)
    print(f"corpus seeding complete: {n} docs")
    return n


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())


if __name__ == "__main__":
    main()
