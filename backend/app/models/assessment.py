"""Assessment, question, result, attendance and topic-mastery tables."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # e.g. "C01-A05"
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Primary topic this assessment targets (many questions may span topics).
    topic_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # quiz|assignment|exam
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text)
    max_points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "assessment_results"
    __table_args__ = (
        Index("ix_result_student_assessment", "student_id", "assessment_id", unique=True),
        Index("ix_result_assessment", "assessment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[Optional[float]] = mapped_column(Float)  # null when missing
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    percentage: Mapped[Optional[float]] = mapped_column(Float)
    is_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Positive => late submission (hours after due). Null when not submitted.
    submission_delay_hours: Mapped[Optional[float]] = mapped_column(Float)


class QuestionResult(Base, TimestampMixin):
    """Per-question outcomes; enables Course->Topic->Student->Question drilldown."""

    __tablename__ = "question_results"
    __table_args__ = (
        Index("ix_qresult_student_question", "student_id", "question_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"
    __table_args__ = (
        Index("ix_att_student_course_date", "student_id", "course_id", "session_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(12), nullable=False)  # present|absent|late


class StudentTopicMastery(Base, TimestampMixin):
    __tablename__ = "student_topic_mastery"
    __table_args__ = (
        Index("ix_mastery_student_topic", "student_id", "topic_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mastery: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-1
    assessments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
