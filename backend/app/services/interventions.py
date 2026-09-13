"""Intervention recommendation, recording, and effectiveness measurement.

Recommendations are derived from a student's actual weaknesses (their stored
feature snapshot, SHAP factors, and weakest topics). Effectiveness is measured
as observed before/after change, always reported with an explicit caveat that
observational data does not establish causal effectiveness.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import Student, Topic
from app.models.assessment import StudentTopicMastery
from app.models.intervention import Intervention, InterventionOutcome
from app.ml import serving

WEAK_MASTERY = 0.60


def _weak_topics(db: Session, student_id: str, limit: int = 3) -> List[dict]:
    rows = db.execute(
        select(Topic.name, StudentTopicMastery.mastery, Topic.id)
        .join(StudentTopicMastery, StudentTopicMastery.topic_id == Topic.id)
        .where(StudentTopicMastery.student_id == student_id)
        .order_by(StudentTopicMastery.mastery)
        .limit(limit)
    ).all()
    return [{"topic_id": r[2], "name": r[0], "mastery_pct": round(r[1] * 100, 1)}
            for r in rows if r[1] is not None and r[1] < WEAK_MASTERY]


def recommend_for_student(db: Session, student_id: str) -> dict:
    if db.get(Student, student_id) is None:
        return {}
    pred = serving.get_student_prediction(db, student_id)
    feats = (pred.features or {}) if pred else {}
    recs: List[dict] = []

    att = feats.get("attendance_pct")
    if att is not None and att < 70:
        recs.append({"type": "attendance intervention", "priority": 1,
                     "reason": f"Attendance is {att:.0f}%, below the 70% guideline."})
    if feats.get("attendance_slope") is not None and feats["attendance_slope"] < -0.02:
        recs.append({"type": "attendance intervention", "priority": 2,
                     "reason": "Attendance is trending downward over the term."})

    for wt in _weak_topics(db, student_id, limit=2):
        recs.append({"type": "prerequisite revision", "priority": 1,
                     "target_topic": wt["name"],
                     "reason": f"Low mastery of {wt['name']} ({wt['mastery_pct']:.0f}%)."})
        recs.append({"type": "targeted practice", "priority": 2,
                     "target_topic": wt["name"],
                     "reason": f"Complete a targeted practice set on {wt['name']}."})

    if feats.get("missed_assignments", 0) and feats["missed_assignments"] >= 2:
        recs.append({"type": "instructor meeting", "priority": 1,
                     "reason": f"{int(feats['missed_assignments'])} missing assignments in the "
                               "feature window."})
    for k, label in (("quiz_avg", "quiz"), ("assignment_avg", "assignment"),
                     ("midterm_avg", "midterm")):
        v = feats.get(k)
        if v is not None and v < 50:
            recs.append({"type": "tutoring", "priority": 2,
                         "reason": f"Low {label} performance ({v:.0f}%)."})
            break

    if pred and pred.risk_label == "HIGH_RISK":
        recs.append({"type": "instructor consultation", "priority": 1,
                     "reason": "Estimated HIGH risk; a one-to-one check-in is advised."})

    # de-duplicate by (type, target) keeping highest priority (lowest number)
    seen = {}
    for r in sorted(recs, key=lambda r: r["priority"]):
        key = (r["type"], r.get("target_topic"))
        if key not in seen:
            seen[key] = r
    ordered = sorted(seen.values(), key=lambda r: r["priority"])

    return {
        "student_id": student_id,
        "risk_label": pred.risk_label if pred else None,
        "risk_probability": round(pred.risk_probability, 3) if pred else None,
        "recommendations": ordered,
        "note": "Recommendations are decision support based on observed weaknesses; "
                "they are not guaranteed to work and require instructor judgement.",
    }


def create_intervention(db: Session, *, student_id: str, type: str, reason: str,
                        course_id: Optional[str] = None, description: Optional[str] = None,
                        expected_outcome: Optional[str] = None,
                        scheduled_date: Optional[date] = None,
                        recommended_by: str = "instructor") -> Intervention:
    iv = Intervention(
        student_id=student_id, course_id=course_id, type=type, reason=reason,
        description=description, expected_outcome=expected_outcome,
        scheduled_date=scheduled_date, recommended_by=recommended_by,
        status="proposed", created_on=datetime.utcnow(),
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return iv


def record_outcome(db: Session, *, intervention_id: int, metric: str,
                   before_value: float, after_value: float,
                   notes: Optional[str] = None) -> Optional[InterventionOutcome]:
    iv = db.get(Intervention, intervention_id)
    if iv is None:
        return None
    outcome = InterventionOutcome(
        intervention_id=intervention_id, metric=metric,
        before_value=before_value, after_value=after_value,
        delta=round(after_value - before_value, 2),
        measured_at=datetime.utcnow(), notes=notes,
    )
    iv.status = "completed"
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def effectiveness(db: Session) -> dict:
    outcomes = db.execute(select(InterventionOutcome)).scalars().all()
    if not outcomes:
        return {"n": 0, "note": "No recorded intervention outcomes yet."}
    deltas = [o.delta for o in outcomes if o.delta is not None]
    improved = sum(1 for d in deltas if d > 0)

    # by intervention type
    by_type: dict = {}
    for o in outcomes:
        iv = db.get(Intervention, o.intervention_id)
        t = iv.type if iv else "unknown"
        by_type.setdefault(t, []).append(o.delta or 0.0)
    type_summary = {
        t: {"n": len(ds), "mean_delta": round(sum(ds) / len(ds), 2)}
        for t, ds in by_type.items()
    }

    mean_delta = round(sum(deltas) / len(deltas), 2) if deltas else 0.0
    return {
        "n": len(outcomes),
        "mean_delta": mean_delta,
        "improved": improved,
        "improved_share": round(improved / len(deltas), 3) if deltas else None,
        "by_type": type_summary,
        "caveat": "These are observational before/after changes on a synthetic dataset. "
                  "They do NOT establish causal effectiveness — there is no control group, "
                  "and improvement may reflect regression to the mean or other factors. "
                  "A randomised or matched comparison would be required for causal claims.",
    }


def list_interventions(db: Session, student_id: Optional[str] = None) -> List[dict]:
    q = select(Intervention).order_by(Intervention.created_on.desc())
    if student_id:
        q = q.where(Intervention.student_id == student_id)
    out = []
    for iv in db.execute(q).scalars().all():
        outcomes = [
            {"metric": o.metric, "before": o.before_value, "after": o.after_value,
             "delta": o.delta}
            for o in iv.outcomes
        ]
        out.append({
            "id": iv.id, "student_id": iv.student_id, "type": iv.type,
            "reason": iv.reason, "status": iv.status,
            "expected_outcome": iv.expected_outcome,
            "recommended_by": iv.recommended_by,
            "scheduled_date": iv.scheduled_date, "outcomes": outcomes,
        })
    return out
