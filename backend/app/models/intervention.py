"""Intervention recommendations, records, and measured outcomes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Intervention(Base, TimestampMixin):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    type: Mapped[str] = mapped_column(String(48), nullable=False)  # tutoring|revision|...
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    recommended_by: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="proposed", nullable=False)
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    outcomes: Mapped[list["InterventionOutcome"]] = relationship(
        back_populates="intervention", cascade="all, delete-orphan"
    )


class InterventionOutcome(Base, TimestampMixin):
    __tablename__ = "intervention_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intervention_id: Mapped[int] = mapped_column(
        ForeignKey("interventions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(48), nullable=False)  # e.g. avg_score
    before_value: Mapped[Optional[float]] = mapped_column(Float)
    after_value: Mapped[Optional[float]] = mapped_column(Float)
    delta: Mapped[Optional[float]] = mapped_column(Float)
    measured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    intervention: Mapped["Intervention"] = relationship(back_populates="outcomes")
