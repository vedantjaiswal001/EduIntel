"""Operational tables: early-warning alerts and audit log."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Alert(Base, TimestampMixin):
    """Early-warning alert surfaced on the dashboard."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False)  # student|course|topic
    entity_id: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # low|medium|high
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base, TimestampMixin):
    """Audit-friendly record of significant actions (writes, model serving)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(120))
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)
