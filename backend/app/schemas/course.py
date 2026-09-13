"""Course and topic API schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CourseRead(ORMModel):
    id: str
    code: str
    title: str
    department: str
    instructor_name: str
    credits: int
    term: str
    difficulty: float


class TopicRead(ORMModel):
    id: str
    course_id: str
    name: str
    sequence: int
    difficulty: float
