"""Student feedback with NLP-derived analysis columns."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Student may be null for anonymized feedback (privacy option).
    student_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instructor_name: Mapped[Optional[str]] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float)  # 1-5 stars, optional
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ---- NLP-derived fields (populated by the feedback engine, nullable) ----
    sentiment: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)  # -1..1
    severity: Mapped[Optional[str]] = mapped_column(String(16))  # low|medium|high
    aspect: Mapped[Optional[str]] = mapped_column(String(40))
    topics: Mapped[Optional[list]] = mapped_column(JSONB)  # list[str]
    issues: Mapped[Optional[list]] = mapped_column(JSONB)  # list[str]
    analysis_method: Mapped[Optional[str]] = mapped_column(String(24))  # rule|transformer|llm
