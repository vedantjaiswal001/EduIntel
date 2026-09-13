"""Executive dashboard overview aggregation.

Returns only computed values. Risk-distribution fields are populated once the
Phase-4 model is trained and predictions exist; until then they are null so
the UI shows an honest empty state rather than fabricated numbers.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics import metrics
from app.analytics.anomaly import detect_assessment_anomalies
from app.analytics.course_health import compute_course_health
from app.analytics.insights import business_insights
from app.models.academic import Course, Enrollment, Student
from app.models.ml import Prediction


def dashboard_overview(db: Session) -> dict:
    n_students = db.execute(select(func.count(Student.id))).scalar() or 0
    n_courses = db.execute(select(func.count(Course.id))).scalar() or 0
    n_enroll = db.execute(select(func.count(Enrollment.id))).scalar() or 0

    course_ids = db.execute(select(Course.id)).scalars().all()
    healths = [compute_course_health(db, c) for c in course_ids]
    health_scores = [h["score"] for h in healths if h and h["score"] is not None]
    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else None

    anomalies = detect_assessment_anomalies(db)

    # Risk distribution from stored predictions (present only after Phase 4).
    risk_rows = db.execute(
        select(Prediction.risk_label, func.count())
        .group_by(Prediction.risk_label)
    ).all()
    risk_distribution = {label: int(c) for label, c in risk_rows} or None

    perf = metrics.platform_performance(db)
    att = metrics.platform_attendance(db)

    return {
        "totals": {"students": n_students, "courses": n_courses, "enrollments": n_enroll},
        "avg_performance": round(perf, 1) if perf is not None else None,
        "attendance_avg": round(att * 100, 1) if att is not None else None,
        "avg_course_health": avg_health,
        "feedback_sentiment": metrics.platform_feedback_sentiment(db),
        "performance_trend": [
            {"sequence": s, "mean_pct": round(v, 1)}
            for s, v in metrics.platform_performance_trend(db)
        ],
        "risk_distribution": risk_distribution,
        "recent_alerts": [
            {"severity": a["severity"], "message": a["message"], "entity_id": a["entity_id"]}
            for a in anomalies[:5]
        ],
        "ai_insights": [i["text"] for i in business_insights(db)],
    }
