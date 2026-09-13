"""Core academic entities: students, courses, topics, enrollments."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    # Human-readable business key used throughout the API (e.g. "S0001").
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # PII minimization: only a synthetic institutional email is stored.
    email: Mapped[Optional[str]] = mapped_column(String(160), unique=True)
    program: Mapped[str] = mapped_column(String(80), nullable=False)
    enrollment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Prior-semester GPA on a 0-10 scale (Indian convention); a legitimate,
    # non-leaky historical feature available before the current term begins.
    prev_gpa: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_synthetic: Mapped[bool] = mapped_column(default=True, nullable=False)

    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # e.g. "C01"
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    instructor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    term: Mapped[str] = mapped_column(String(24), nullable=False, default="2026-S1")
    # Latent difficulty (0-1) used by the synthetic generator; also a
    # transparent input to the course-health score. Documented, not hidden.
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    topics: Mapped[List["Topic"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # e.g. "C01-T03"
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="topics")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("ix_enrollment_student_course", "student_id", "course_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    term: Mapped[str] = mapped_column(String(24), nullable=False, default="2026-S1")
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    enrolled_on: Mapped[Optional[date]] = mapped_column(Date)
    # Final numeric grade for the term (0-100); nullable until the term ends.
    # NOTE: this is an outcome and must never be used as a model feature.
    final_grade: Mapped[Optional[float]] = mapped_column(Float)

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")
