"""Course and topic read endpoints. Health/analytics added in Phase 3."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import topics as topic_analytics
from app.analytics.course_health import compute_course_health
from app.api.deps import get_db
from app.models.academic import Course, Topic
from app.schemas.course import CourseRead, TopicRead

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.execute(select(Course).order_by(Course.id)).scalars().all()


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: str, db: Session = Depends(get_db)) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get("/{course_id}/topics", response_model=list[TopicRead])
def list_course_topics(course_id: str, db: Session = Depends(get_db)) -> list[Topic]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return (
        db.execute(
            select(Topic).where(Topic.course_id == course_id).order_by(Topic.sequence)
        )
        .scalars()
        .all()
    )


@router.get("/{course_id}/health")
def course_health(course_id: str, db: Session = Depends(get_db)) -> dict:
    result = compute_course_health(db, course_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return result


@router.get("/{course_id}/topics/performance")
def course_topics_performance(course_id: str, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return topic_analytics.course_topics_performance(db, course_id)
