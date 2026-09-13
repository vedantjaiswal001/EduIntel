"""Transparent course-health score.

The score is a documented weighted average of five components, each on a 0-100
scale. There is no black box: the component values, the weights, and the
resulting arithmetic are all returned so the number can be audited and
explained.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.analytics import metrics
from app.models.academic import Course

# Documented, fixed weights (sum to 1.0). Exposed via the API for transparency.
COMPONENT_WEIGHTS: Dict[str, float] = {
    "performance": 0.30,
    "attendance": 0.20,
    "topic_mastery": 0.20,
    "feedback": 0.15,
    "trend": 0.15,
}


def _trend_to_score(slope: Optional[float]) -> Optional[float]:
    """Map a per-assessment score slope to a 0-100 component.

    A flat trend maps to 50; each +1 pt/assessment moves it ~+8, clipped.
    """
    if slope is None:
        return None
    return max(0.0, min(100.0, 50.0 + slope * 8.0))


def compute_course_health(db: Session, course_id: str) -> Optional[dict]:
    course = db.get(Course, course_id)
    if course is None:
        return None

    performance = metrics.course_performance(db, course_id)
    attendance = metrics.course_attendance(db, course_id)
    mastery = metrics.course_topic_mastery(db, course_id)
    fb = metrics.course_feedback(db, course_id)
    trend_points = metrics.course_score_trend(db, course_id)
    slope = metrics.linear_slope([(float(s), v) for s, v in trend_points])

    components = {
        "performance": performance,
        "attendance": attendance * 100 if attendance is not None else None,
        "topic_mastery": mastery * 100 if mastery is not None else None,
        # Map mean rating (1-5) to 0-100; None when no feedback.
        "feedback": ((fb["mean_rating"] - 1) / 4 * 100) if fb["mean_rating"] else None,
        "trend": _trend_to_score(slope),
    }

    # Weighted average over the components that have data; renormalise weights
    # so a missing component does not silently deflate the score.
    used = {k: v for k, v in components.items() if v is not None}
    wsum = sum(COMPONENT_WEIGHTS[k] for k in used)
    score = (
        sum(components[k] * COMPONENT_WEIGHTS[k] for k in used) / wsum if wsum else None
    )

    weakest: List[str] = sorted(used, key=lambda k: used[k])[:2]

    return {
        "course_id": course_id,
        "course_title": course.title,
        "score": round(score, 1) if score is not None else None,
        "components": {k: (round(v, 1) if v is not None else None)
                       for k, v in components.items()},
        "weights": COMPONENT_WEIGHTS,
        "pass_rate": metrics.course_pass_rate(db, course_id),
        "feedback_n": fb["n"],
        "score_trend": [{"sequence": s, "mean_pct": round(v, 1)} for s, v in trend_points],
        "explanation": _explain(course.title, score, components, weakest),
    }


def _explain(title: str, score, components, weakest) -> str:
    if score is None:
        return f"Insufficient data to score {title}."
    labels = {
        "performance": "assessment performance",
        "attendance": "attendance",
        "topic_mastery": "topic mastery",
        "feedback": "student feedback",
        "trend": "performance trend",
    }
    weak_txt = " and ".join(labels[w] for w in weakest) if weakest else "no single area"
    band = "strong" if score >= 75 else "moderate" if score >= 60 else "at-risk"
    return (
        f"{title} has a {band} health score of {score:.0f}/100. The score is most "
        f"held back by {weak_txt}. Components are a documented weighted average; "
        f"see `weights` for the exact formula."
    )
