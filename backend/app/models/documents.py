"""RAG knowledge-base documents and their embedded chunks (pgvector)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)  # lecture|syllabus|...
    filename: Mapped[Optional[str]] = mapped_column(String(240))
    num_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="processed", nullable=False)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[Optional[int]] = mapped_column(Integer)
    section: Mapped[Optional[str]] = mapped_column(String(160))
    topic: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    doc_type: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # pgvector embedding; dimension matches the configured embedding model.
    embedding: Mapped[Optional[list]] = mapped_column(Vector(settings.EMBEDDING_DIM))

    document: Mapped["Document"] = relationship(back_populates="chunks")
