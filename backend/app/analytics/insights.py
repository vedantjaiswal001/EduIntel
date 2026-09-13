"""Business-intelligence insights.

Each insight is a short natural-language statement whose numbers are computed
from the database — the LLM never invents figures. Risk-based insights that
depend on the ML model are added in Phase 4; these use observed outcomes.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.analytics import topics as topic_analytics
from app.analytics.anomaly import detect_assessment_anomalies
from app.analytics.course_health import compute_course_health
from app.models.academic import Course, Enrollment


def business_insights(db: Session) -> List[dict]:
    insights: List[dict] = []

    # --- concentration of failing enrollments (observed outcome, not ML risk)
    rows = db.execute(
        select(
            Enrollment.course_id,
            func.count().label("total"),
            func.sum(case((Enrollment.final_grade < 50, 1), else_=0)).label("fail"),
        )
        .where(Enrollment.final_grade.isnot(None))
        .group_by(Enrollment.course_id)
    ).all()
    total_enroll = sum(r.total for r in rows)
    total_fail = sum(int(r.fail or 0) for r in rows)
    if total_fail > 0 and rows:
        ranked = sorted(rows, key=lambda r: int(r.fail or 0), reverse=True)
        top3 = ranked[:3]
        fail_share = sum(int(r.fail or 0) for r in top3) / total_fail
        enroll_share = sum(r.total for r in top3) / total_enroll
        names = ", ".join(db.get(Course, r.course_id).title for r in top3)
        insights.append({
            "kind": "concentration",
            "text": (
                f"3 courses ({names}) account for {fail_share*100:.0f}% of failing "
                f"enrollments despite representing {enroll_share*100:.0f}% of enrollment."
            ),
            "metrics": {"fail_share": round(fail_share, 3), "enroll_share": round(enroll_share, 3)},
        })

    # --- weakest topics platform-wide
    weak = topic_analytics.weakest_topics(db, limit=3)
    if weak:
        wt = ", ".join(f"{w['name']} ({w['mastery_pct']:.0f}%)" for w in weak)
        insights.append({
            "kind": "weak_topics",
            "text": f"The weakest topics platform-wide are {wt}.",
            "metrics": {"topics": weak},
        })

    # --- lowest course-health courses
    healths = []
    for c in db.execute(select(Course.id)).scalars().all():
        h = compute_course_health(db, c)
        if h and h["score"] is not None:
            healths.append((c, h["course_title"], h["score"]))
    healths.sort(key=lambda x: x[2])
    if healths:
        cid, title, score = healths[0]
        insights.append({
            "kind": "course_health",
            "text": f"{title} has the lowest course-health score at {score:.0f}/100.",
            "metrics": {"course_id": cid, "score": score},
        })

    # --- anomaly summary
    anomalies = detect_assessment_anomalies(db)
    if anomalies:
        top = anomalies[0]
        insights.append({
            "kind": "anomaly",
            "text": f"{len(anomalies)} assessment anomaly(ies) detected; most severe: {top['message']}",
            "metrics": {"count": len(anomalies)},
        })

    return insights
