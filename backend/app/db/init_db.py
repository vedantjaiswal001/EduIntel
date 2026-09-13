"""Database initialization: enable pgvector and create all tables.

This is intentionally lightweight (create_all) so the demo spins up with a
single command. A production project would drive schema changes through the
Alembic migrations in `backend/alembic/`.
"""
from __future__ import annotations

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import engine

# Ensure every model is imported so metadata is complete.
import app.models  # noqa: F401

logger = get_logger(__name__)


def init_db() -> None:
    """Create the pgvector extension (if available) and all tables."""
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension ensured")
        except Exception as exc:  # pragma: no cover - depends on DB privileges
            logger.warning("Could not create pgvector extension: %s", exc)
    Base.metadata.create_all(bind=engine)
    # Create the ANN index for vector search after the table exists.
    _create_vector_index()
    logger.info("All tables created")


def _create_vector_index() -> None:
    """Create an HNSW index on document embeddings for fast, high-recall search.

    HNSW is preferred over IVFFlat: it needs no training set (correct even when
    built on an empty table before ingestion) and gives near-exact recall at
    small scale, avoiding IVFFlat's lists/probes pitfalls.
    """
    stmt = text(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    try:
        with engine.begin() as conn:
            conn.execute(stmt)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not create vector index (ok if no rows yet): %s", exc)


if __name__ == "__main__":
    from app.core.logging import configure_logging

    configure_logging()
    init_db()
