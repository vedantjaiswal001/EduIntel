"""Database engine and session management."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# `pool_pre_ping` avoids stale connections after the DB restarts (common in
# docker-compose setups). `future=True` selects SQLAlchemy 2.0 semantics.
engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    future=True,
    echo=False,
    # Force UTF-8 so any Unicode content (names, feedback, documents) is safe
    # regardless of the client's locale.
    connect_args={"client_encoding": "utf8"},
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
