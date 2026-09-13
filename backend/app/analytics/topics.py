"""Topic intelligence: mastery, weak-topic detection, and drilldown."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import Topic
from app.models.assessment import StudentTopicMastery

# A topic is flagged "weak" when average mastery is below this fraction.
WEAK_TOPIC_THRESHOLD = 0.60


def course_topics_performance(db: Session, course_id: str) -> List[dict]:
    """Every topic in a course with mean mastery, ranked weakest-first."""
    rows = db.execute(
        select(
            Topic.id, Topic.name, Topic.sequence, Topic.difficulty,
            func.avg(StudentTopicMastery.mastery).label("mastery"),
            func.count(StudentTopicMastery.id).label("n"),
        )
        .join(StudentTopicMastery, StudentTopicMastery.topic_id == Topic.id, isouter=True)
        .where(Topic.course_id == course_id)
        .group_by(Topic.id, Topic.name, Topic.sequence, Topic.difficulty)
        .order_by(Topic.sequence)
    ).all()
    out = []
    for r in rows:
        m = float(r.mastery) if r.mastery is not None else None
        out.append({
            "topic_id": r.id,
            "name": r.name,
            "sequence": r.sequence,
            "difficulty": r.difficulty,
            "mastery_pct": round(m * 100, 1) if m is not None else None,
            "students": int(r.n),
            "is_weak": (m is not None and m < WEAK_TOPIC_THRESHOLD),
        })
    return out


def topic_performance(db: Session, topic_id: str) -> Optional[dict]:
    topic = db.get(Topic, topic_id)
    if topic is None:
        return None
    rows = db.execute(
        select(StudentTopicMastery.mastery).where(StudentTopicMastery.topic_id == topic_id)
    ).scalars().all()
    n = len(rows)
    mean = sum(rows) / n if n else None
    # mastery distribution buckets
    buckets = {"0-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for m in rows:
        p = m * 100
        key = "0-40" if p < 40 else "40-60" if p < 60 else "60-80" if p < 80 else "80-100"
        buckets[key] += 1
    return {
        "topic_id": topic_id,
        "name": topic.name,
        "course_id": topic.course_id,
        "difficulty": topic.difficulty,
        "mean_mastery_pct": round(mean * 100, 1) if mean is not None else None,
        "students": n,
        "is_weak": (mean is not None and mean < WEAK_TOPIC_THRESHOLD),
        "distribution": buckets,
    }


def topic_students(db: Session, topic_id: str, limit: int = 200) -> List[dict]:
    """Per-student mastery for a topic (Course->Topic->Student drilldown)."""
    rows = db.execute(
        select(StudentTopicMastery.student_id, StudentTopicMastery.mastery,
               StudentTopicMastery.assessments_count)
        .where(StudentTopicMastery.topic_id == topic_id)
        .order_by(StudentTopicMastery.mastery)
        .limit(limit)
    ).all()
    return [
        {"student_id": sid, "mastery_pct": round(m * 100, 1), "assessments": c}
        for sid, m, c in rows
    ]


def weakest_topics(db: Session, limit: int = 10) -> List[dict]:
    """Platform-wide weakest topics (for BI + dashboard)."""
    rows = db.execute(
        select(
            Topic.id, Topic.name, Topic.course_id,
            func.avg(StudentTopicMastery.mastery).label("mastery"),
        )
        .join(StudentTopicMastery, StudentTopicMastery.topic_id == Topic.id)
        .group_by(Topic.id, Topic.name, Topic.course_id)
        .order_by(func.avg(StudentTopicMastery.mastery))
        .limit(limit)
    ).all()
    return [
        {"topic_id": r.id, "name": r.name, "course_id": r.course_id,
         "mastery_pct": round(float(r.mastery) * 100, 1)}
        for r in rows
    ]
