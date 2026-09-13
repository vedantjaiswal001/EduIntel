"""Shared pytest fixtures.

Unit tests run without a database. API/integration tests use the configured
database and are skipped automatically when it is unavailable or unseeded, so
`pytest` succeeds in any environment (the DB-backed ones run in CI/dev where the
stack is up).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.main import app


def _db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _seeded() -> bool:
    try:
        with engine.connect() as c:
            return (c.execute(text("SELECT COUNT(*) FROM students")).scalar() or 0) > 0
    except Exception:
        return False


DB_AVAILABLE = _db_ok()
DB_SEEDED = DB_AVAILABLE and _seeded()

requires_db = pytest.mark.skipif(not DB_SEEDED, reason="seeded database not available")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
