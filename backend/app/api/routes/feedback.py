"""Feedback intelligence endpoints (aggregation + NLP analysis)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.feedback_agg import feedback_insights
from app.api.deps import get_db
from app.models.academic import Topic
from app.nlp.analyzer import FeedbackAnalyzer
from app.nlp.pipeline import compare_methods

router = APIRouter(prefix="/feedback", tags=["feedback"])


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    method: str = Field(default="rule", pattern="^(rule|transformer|llm)$")


@router.get("/insights")
def insights(
    course_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return feedback_insights(db, course_id=course_id)


@router.post("/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    vocab = db.execute(select(Topic.name).distinct()).scalars().all()
    analyzer = FeedbackAnalyzer(topic_vocab=vocab)
    return analyzer.analyze(body.text, method=body.method)


@router.get("/method-comparison")
def method_comparison(
    sample: int = Query(150, ge=10, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    return compare_methods(db, sample=sample)
