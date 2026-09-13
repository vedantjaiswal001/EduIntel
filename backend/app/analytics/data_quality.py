"""Data-quality engine.

Scans the loaded data for the issues that would corrupt model training and
analytics, and returns an auditable report. Every number is computed by a
real query; nothing is assumed clean.
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.academic import Student
from app.models.assessment import AssessmentResult, Attendance
from app.models.feedback import Feedback

VALID_ATTENDANCE = ("present", "late", "absent")


def run_data_quality(db: Session) -> dict:
    checks: Dict[str, dict] = {}

    def scalar(stmt) -> int:
        return int(db.execute(stmt).scalar() or 0)

    n_results = scalar(select(func.count(AssessmentResult.id)))
    n_attendance = scalar(select(func.count(Attendance.id)))
    n_feedback = scalar(select(func.count(Feedback.id)))
    n_students = scalar(select(func.count(Student.id)))
    rows_processed = n_results + n_attendance + n_feedback + n_students

    # --- missing values: results not flagged missing but with null percentage
    missing_pct = scalar(
        select(func.count(AssessmentResult.id)).where(
            AssessmentResult.is_missing.is_(False), AssessmentResult.percentage.is_(None)
        )
    )
    checks["missing_values"] = {
        "count": missing_pct,
        "detail": "assessment_results not marked missing but with a null percentage",
    }

    # --- duplicates: duplicate (student, assessment) pairs
    dup = db.execute(text(
        "SELECT COUNT(*) FROM (SELECT student_id, assessment_id FROM assessment_results "
        "GROUP BY student_id, assessment_id HAVING COUNT(*) > 1) d"
    )).scalar() or 0
    checks["duplicates"] = {"count": int(dup), "detail": "duplicate student/assessment result rows"}

    # --- impossible values
    bad_pct = scalar(select(func.count(AssessmentResult.id)).where(
        (AssessmentResult.percentage < 0) | (AssessmentResult.percentage > 100)))
    bad_gpa = scalar(select(func.count(Student.id)).where(
        (Student.prev_gpa < 0) | (Student.prev_gpa > 10)))
    bad_rating = scalar(select(func.count(Feedback.id)).where(
        Feedback.rating.isnot(None) & ((Feedback.rating < 1) | (Feedback.rating > 5))))
    checks["impossible_values"] = {
        "count": bad_pct + bad_gpa + bad_rating,
        "detail": "percentages outside 0-100, GPA outside 0-10, or ratings outside 1-5",
    }

    # --- invalid attendance status
    invalid_att = scalar(select(func.count(Attendance.id)).where(
        Attendance.status.notin_(VALID_ATTENDANCE)))
    checks["invalid_attendance"] = {"count": invalid_att, "detail": "attendance status not in present/late/absent"}

    # --- referential integrity (orphans)
    orphans = db.execute(text(
        "SELECT COUNT(*) FROM assessment_results ar "
        "LEFT JOIN students s ON s.id = ar.student_id WHERE s.id IS NULL"
    )).scalar() or 0
    checks["inconsistent_ids"] = {"count": int(orphans), "detail": "results referencing a missing student"}

    # --- outliers: percentages more than 4 SD from the global mean
    stats = db.execute(select(func.avg(AssessmentResult.percentage),
                              func.stddev_pop(AssessmentResult.percentage))).one()
    mean, sd = (float(stats[0]) if stats[0] is not None else 0.0,
                float(stats[1]) if stats[1] is not None else 0.0)
    outliers = 0
    if sd > 1e-9:
        lo, hi = mean - 4 * sd, mean + 4 * sd
        outliers = scalar(select(func.count(AssessmentResult.id)).where(
            (AssessmentResult.percentage < lo) | (AssessmentResult.percentage > hi)))
    checks["outliers"] = {"count": outliers, "detail": "assessment percentages beyond 4 SD"}

    total_issues = sum(c["count"] for c in checks.values())
    # A simple quality score: 100 minus issue rate (%), floored at 0.
    quality_score = max(0.0, 100.0 - (total_issues / rows_processed * 100 if rows_processed else 0))

    return {
        "rows_processed": rows_processed,
        "table_counts": {
            "assessment_results": n_results, "attendance": n_attendance,
            "feedback": n_feedback, "students": n_students,
        },
        "checks": checks,
        "total_issues": total_issues,
        "quality_score": round(quality_score, 2),
    }
