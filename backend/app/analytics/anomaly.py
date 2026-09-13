"""Anomaly detection over assessment and attendance aggregates.

Two methods are computed and compared, as required:
  * a classical **z-score** method (within-course standardisation), and
  * **Isolation Forest** (multivariate, unsupervised).

Surfacing where the two agree gives administrators a defensible signal rather
than a single opaque flag.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentResult

Z_THRESHOLD = 2.5
CONTAMINATION = 0.08


def _assessment_frame(db: Session) -> List[dict]:
    missing_expr = func.avg(case((AssessmentResult.is_missing.is_(True), 1.0), else_=0.0))
    rows = db.execute(
        select(
            Assessment.id,
            Assessment.course_id,
            Assessment.title,
            func.avg(AssessmentResult.percentage).label("mean_pct"),
            missing_expr.label("missing_rate"),
            func.count(AssessmentResult.id).label("n"),
        )
        .join(AssessmentResult, AssessmentResult.assessment_id == Assessment.id)
        .group_by(Assessment.id, Assessment.course_id, Assessment.title)
    ).all()
    return [
        {
            "assessment_id": r.id,
            "course_id": r.course_id,
            "title": r.title,
            "mean_pct": float(r.mean_pct),
            "missing_rate": float(r.missing_rate),
            "n": int(r.n),
        }
        for r in rows
    ]


def detect_assessment_anomalies(db: Session) -> List[dict]:
    data = _assessment_frame(db)
    if len(data) < 3:
        return []

    # ---- z-score within each course (deviation from course mean of means) ----
    by_course: Dict[str, List[dict]] = {}
    for d in data:
        by_course.setdefault(d["course_id"], []).append(d)
    for course_id, items in by_course.items():
        means = np.array([i["mean_pct"] for i in items])
        mu, sd = means.mean(), means.std(ddof=0)
        for i in items:
            i["z"] = (i["mean_pct"] - mu) / sd if sd > 1e-9 else 0.0
            i["dev"] = i["mean_pct"] - mu
            i["z_flag"] = abs(i["z"]) >= Z_THRESHOLD

    # ---- Isolation Forest on [deviation-from-course-mean, missing_rate] ----
    try:
        from sklearn.ensemble import IsolationForest

        X = np.array([[d["dev"], d["missing_rate"] * 100] for d in data])
        iso = IsolationForest(contamination=CONTAMINATION, random_state=42)
        pred = iso.fit_predict(X)  # -1 = outlier
        scores = iso.score_samples(X)
        for d, p, s in zip(data, pred, scores):
            d["iso_flag"] = bool(p == -1)
            d["iso_score"] = float(s)
    except Exception:  # pragma: no cover - sklearn always present in this project
        for d in data:
            d["iso_flag"] = False
            d["iso_score"] = None

    anomalies = []
    for d in data:
        if not (d["z_flag"] or d["iso_flag"]):
            continue
        methods = [m for m, f in (("z-score", d["z_flag"]), ("isolation-forest", d["iso_flag"])) if f]
        severity = "high" if (d["z_flag"] and d["iso_flag"]) else "medium"
        direction = "below" if d["z"] < 0 else "above"
        anomalies.append({
            "scope": "assessment",
            "entity_id": d["assessment_id"],
            "course_id": d["course_id"],
            "severity": severity,
            "methods": methods,
            "z_score": round(d["z"], 2),
            "mean_pct": round(d["mean_pct"], 1),
            "missing_rate": round(d["missing_rate"], 3),
            "message": (
                f"{d['assessment_id']} ({d['title']}) mean {d['mean_pct']:.1f}% is "
                f"{abs(d['z']):.1f} SD {direction} the course average"
                + (" and flagged by Isolation Forest" if d["iso_flag"] and d["z_flag"] else "")
                + "."
            ),
        })
    anomalies.sort(key=lambda a: (a["severity"] != "high", a["z_score"]))
    return anomalies


def detect_attendance_anomalies(db: Session) -> List[dict]:
    """Course-weeks whose attendance is an outlier vs that course's own weeks."""
    from app.models.assessment import Attendance

    weight = case((Attendance.status == "present", 1.0),
                  (Attendance.status == "late", 0.5), else_=0.0)
    rows = db.execute(
        select(Attendance.course_id, Attendance.week, func.avg(weight))
        .group_by(Attendance.course_id, Attendance.week)
    ).all()
    by_course: Dict[str, List[tuple]] = {}
    for cid, week, rate in rows:
        by_course.setdefault(cid, []).append((int(week), float(rate)))

    anomalies = []
    for cid, weeks in by_course.items():
        rates = np.array([r for _, r in weeks])
        mu, sd = rates.mean(), rates.std(ddof=0)
        if sd < 1e-9:
            continue
        for week, rate in weeks:
            z = (rate - mu) / sd
            if z <= -Z_THRESHOLD:
                anomalies.append({
                    "scope": "attendance",
                    "entity_id": f"{cid}-W{week:02d}",
                    "course_id": cid,
                    "severity": "medium",
                    "methods": ["z-score"],
                    "z_score": round(z, 2),
                    "message": (
                        f"{cid} week {week} attendance {rate*100:.0f}% is "
                        f"{abs(z):.1f} SD below the course's weekly average."
                    ),
                })
    return anomalies
