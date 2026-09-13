"""Semantic search / RAG retrieval endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.rag.retrieval import semantic_search

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQuery(BaseModel):
    query: str = Field(min_length=1)
    course_id: str | None = None
    topic: str | None = None
    doc_type: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    rerank: bool = True


@router.post("/query")
def rag_query(body: RagQuery, db: Session = Depends(get_db)) -> dict:
    return semantic_search(
        db, body.query, course_id=body.course_id, topic=body.topic,
        doc_type=body.doc_type, top_k=body.top_k, rerank=body.rerank)
