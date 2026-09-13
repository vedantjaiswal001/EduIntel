"""Topic intelligence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics import topics as topic_analytics
from app.api.deps import get_db

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/weak")
def weak_topics(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)) -> list[dict]:
    return topic_analytics.weakest_topics(db, limit=limit)


@router.get("/{topic_id}/performance")
def topic_performance(topic_id: str, db: Session = Depends(get_db)) -> dict:
    result = topic_analytics.topic_performance(db, topic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@router.get("/{topic_id}/students")
def topic_students(
    topic_id: str,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    return topic_analytics.topic_students(db, topic_id, limit=limit)
