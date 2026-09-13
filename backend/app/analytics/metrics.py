"""Low-level analytic aggregate queries.

These are the shared, reusable SQL aggregations the higher-level analytics
(course health, topic intelligence, dashboard, BI) build on. Everything is a
real query against the database — no value is fabricated. Functions return
``None`` when there is no data, so callers can render honest empty states.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.academic import Course, Enrollment, Topic
from app.models.assessment import (
    Assessment,
    AssessmentResult,
    Attendance,
    StudentTopicMastery,
)
from app.models.feedback import Feedback

# Present counts fully, late as half, absent as zero.
_ATT_WEIGHT = case(
    (Attendance.status == "present", 1.0),
    (Attendance.status == "late", 0.5),
    else_=0.0,
)


def course_performance(db: Session, course_id: str) -> Optional[float]:
    """Mean assessment percentage for a course (0-100)."""
    stmt = (
        select(func.avg(AssessmentResult.percentage))
        .join(Assessment, Assessment.id == AssessmentResult.assessment_id)
        .where(Assessment.course_id == course_id)
    )
    val = db.execute(stmt).scalar()
    return float(val) if val is not None else None


def course_attendance(db: Session, course_id: str) -> Optional[float]:
    """Mean weighted attendance rate for a course (0-1)."""
    val = db.execute(
        select(func.avg(_ATT_WEIGHT)).where(Attendance.course_id == course_id)
    ).scalar()
    return float(val) if val is not None else None


def course_topic_mastery(db: Session, course_id: str) -> Optional[float]:
    """Mean topic mastery for a course (0-1)."""
    val = db.execute(
        select(func.avg(StudentTopicMastery.mastery)).where(
            StudentTopicMastery.course_id == course_id
        )
    ).scalar()
    return float(val) if val is not None else None


def course_feedback(db: Session, course_id: str) -> Dict[str, float]:
    """Feedback summary from ratings (rating-based; NLP sentiment in Phase 7)."""
    rows = db.execute(
        select(Feedback.rating).where(
            Feedback.course_id == course_id, Feedback.rating.isnot(None)
        )
    ).scalars().all()
    n = len(rows)
    if n == 0:
        return {"n": 0, "mean_rating": None, "positive": 0.0, "neutral": 0.0, "negative": 0.0}
    pos = sum(1 for r in rows if r >= 4) / n
    neg = sum(1 for r in rows if r <= 2) / n
    neu = 1.0 - pos - neg
    return {
        "n": n,
        "mean_rating": sum(rows) / n,
        "positive": pos,
        "neutral": neu,
        "negative": neg,
    }


def course_pass_rate(db: Session, course_id: str) -> Optional[float]:
    """Fraction of enrollments with final_grade >= 50 (0-1)."""
    total = db.execute(
        select(func.count()).where(
            Enrollment.course_id == course_id, Enrollment.final_grade.isnot(None)
        )
    ).scalar()
    if not total:
        return None
    passed = db.execute(
        select(func.count()).where(
            Enrollment.course_id == course_id, Enrollment.final_grade >= 50
        )
    ).scalar()
    return float(passed) / float(total)


def course_score_trend(db: Session, course_id: str) -> List[Tuple[int, float]]:
    """Mean percentage by assessment sequence (ordered), for trend/sparkline."""
    stmt = (
        select(Assessment.sequence, func.avg(AssessmentResult.percentage))
        .join(AssessmentResult, AssessmentResult.assessment_id == Assessment.id)
        .where(Assessment.course_id == course_id)
        .group_by(Assessment.sequence)
        .order_by(Assessment.sequence)
    )
    return [(int(seq), float(avg)) for seq, avg in db.execute(stmt).all()]


def linear_slope(points: List[Tuple[float, float]]) -> Optional[float]:
    """Ordinary least-squares slope of y over x. None if < 2 distinct x."""
    if len(points) < 2:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / denom


# ---- platform-level aggregates (dashboard) ------------------------------- #

def platform_performance(db: Session) -> Optional[float]:
    val = db.execute(select(func.avg(AssessmentResult.percentage))).scalar()
    return float(val) if val is not None else None


def platform_attendance(db: Session) -> Optional[float]:
    val = db.execute(select(func.avg(_ATT_WEIGHT))).scalar()
    return float(val) if val is not None else None


def platform_performance_trend(db: Session) -> List[Tuple[int, float]]:
    """Mean percentage by assessment sequence across all courses."""
    stmt = (
        select(Assessment.sequence, func.avg(AssessmentResult.percentage))
        .join(AssessmentResult, AssessmentResult.assessment_id == Assessment.id)
        .group_by(Assessment.sequence)
        .order_by(Assessment.sequence)
    )
    return [(int(seq), float(avg)) for seq, avg in db.execute(stmt).all()]


def platform_feedback_sentiment(db: Session) -> Dict[str, float]:
    rows = db.execute(select(Feedback.rating).where(Feedback.rating.isnot(None))).scalars().all()
    n = len(rows)
    if n == 0:
        return {"n": 0, "positive": 0.0, "neutral": 0.0, "negative": 0.0}
    pos = sum(1 for r in rows if r >= 4) / n
    neg = sum(1 for r in rows if r <= 2) / n
    return {"n": n, "positive": pos, "neutral": 1 - pos - neg, "negative": neg}
