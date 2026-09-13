"""Shared Pydantic schema utilities."""
from __future__ import annotations

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base schema that reads attributes from ORM objects."""

    model_config = {"from_attributes": True}


class Page(BaseModel, Generic[T]):
    """A simple paginated response envelope."""

    items: List[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    detail: str


class HealthStatus(BaseModel):
    status: str = "ok"
    service: str
    version: str
    database: str = Field(description="'up' or 'down'")
