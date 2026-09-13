"""Student API schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class StudentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    program: str = Field(min_length=1, max_length=80)
    enrollment_year: int = Field(ge=2000, le=2100)
    prev_gpa: float = Field(ge=0.0, le=10.0, default=0.0)


class StudentCreate(StudentBase):
    id: str = Field(min_length=1, max_length=16, description="Business key, e.g. S0001")


class StudentRead(StudentBase, ORMModel):
    id: str
    is_synthetic: bool = True


class StudentSummary(ORMModel):
    """Compact student record used in lists and risk tables."""

    id: str
    name: str
    program: str
