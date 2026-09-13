"""Common API dependencies."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from app.db.session import get_db  # re-exported for convenience

__all__ = ["get_db", "PaginationParams", "pagination"]


@dataclass
class PaginationParams:
    limit: int
    offset: int


def pagination(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)
