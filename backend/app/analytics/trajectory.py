"""Student learning-trajectory analysis (time-series).

Builds time-ordered score / attendance / topic-mastery series for a student and
computes moving averages, slope, volatility, a trend label, change-points, and
a genuine **risk trajectory** — the active model's HIGH-risk probability
recomputed at successive points in the term using only the data available then.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.ml import registry
from app.ml.features import SEQ_TO_WEEK, build_feature_frame

RISK_CHECKPOINTS = [1, 3, 5, 7]  # quiz1, quiz2, midterm, quiz3
DECLINE_SLOPE = -1.5             # pts/assessment considered a declining trend


def _student_frames(engine: Engine, sid: str) -> dict:
    p = {"sid": sid}
    res = pd.read_sql(
        "SELECT ar.student_id, a.course_id, a.sequence, a.kind, ar.percentage, "
        "ar.is_missing, ar.submission_delay_hours, a.assessment_date "
        "FROM assessment_results ar JOIN assessments a "
        "ON a.id = ar.assessment_id WHERE ar.student_id = %(sid)s",
        engine, params=p)
    att = pd.read_sql(
        "SELECT student_id, course_id, week, status FROM attendance "
        "WHERE student_id = %(sid)s", engine, params=p)
    mastery = pd.read_sql(
        "SELECT student_id, topic_id, mastery FROM student_topic_mastery "
        "WHERE student_id = %(sid)s", engine, params=p)
    students = pd.read_sql(
        "SELECT id AS student_id, prev_gpa FROM students WHERE id = %(sid)s", engine, params=p)
    enroll = pd.read_sql(
        "SELECT student_id, course_id, final_grade FROM enrollments "
        "WHERE student_id = %(sid)s", engine, params=p)
    return {"res": res, "att": att, "mastery": mastery, "students": students, "enroll": enroll}


def _slope(x, y) -> Optional[float]:
    if len(x) < 2 or np.ptp(x) == 0:
        return None
    return float(np.polyfit(x, y, 1)[0])


def _moving_average(vals: List[float], window: int = 3) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(vals)):
        lo = max(0, i - window + 1)
        out.append(round(float(np.mean(vals[lo:i + 1])), 1))
    return out


def _change_points(seqs: List[int], vals: List[float], drop: float = 10.0) -> List[dict]:
    cps = []
    for i in range(1, len(vals)):
        delta = vals[i] - vals[i - 1]
        if delta <= -drop:
            cps.append({"at_sequence": seqs[i], "drop": round(delta, 1)})
    return cps


def student_trajectory(db: Session, engine: Engine, sid: str) -> Optional[dict]:
    frames = _student_frames(engine, sid)
    if frames["students"].empty:
        return None
    res = frames["res"]
    if res.empty:
        return {"student_id": sid, "score_series": [], "attendance_series": [],
                "risk_trajectory": [], "topic_mastery": [], "summary": {}}

    # ---- score series: mean percentage per assessment sequence (<=7) ----
    win = res[res["sequence"] <= 7]
    grp = win.groupby("sequence")["percentage"].mean().sort_index()
    seqs = [int(s) for s in grp.index]
    scores = [round(float(v), 1) for v in grp.values]
    score_series = [
        {"sequence": s, "week": SEQ_TO_WEEK.get(s), "mean_pct": v,
         "moving_avg": ma}
        for s, v, ma in zip(seqs, scores, _moving_average(scores))
    ]

    slope = _slope(np.array(seqs, float), np.array(scores, float))
    volatility = float(np.std(scores)) if len(scores) > 1 else 0.0
    trend = ("DECLINING" if slope is not None and slope <= DECLINE_SLOPE
             else "IMPROVING" if slope is not None and slope >= 1.5 else "STABLE")

    # ---- attendance series: weighted weekly rate ----
    att = frames["att"].copy()
    att["w"] = att["status"].map({"present": 1.0, "late": 0.5, "absent": 0.0})
    aw = att[att["week"] <= 12].groupby("week")["w"].mean().sort_index()
    attendance_series = [{"week": int(w), "rate": round(float(v) * 100, 1)}
                         for w, v in aw.items()]
    att_slope = _slope(np.array(list(aw.index), float), np.array(list(aw.values), float))

    # ---- topic mastery ----
    topic_mastery = [
        {"topic_id": t, "mastery_pct": round(float(m) * 100, 1)}
        for t, m in frames["mastery"].set_index("topic_id")["mastery"].sort_values().items()
    ]

    # ---- risk trajectory: model HIGH-prob at successive cutoffs ----
    risk_trajectory = _risk_trajectory(db, frames, sid)

    return {
        "student_id": sid,
        "score_series": score_series,
        "attendance_series": attendance_series,
        "topic_mastery": topic_mastery,
        "risk_trajectory": risk_trajectory,
        "summary": {
            "score_slope": round(slope, 2) if slope is not None else None,
            "attendance_slope": round(att_slope, 3) if att_slope is not None else None,
            "volatility": round(volatility, 2),
            "trend": trend,
            "change_points": _change_points(seqs, scores),
            "deteriorating": trend == "DECLINING",
        },
    }


def _risk_trajectory(db: Session, frames: dict, sid: str) -> List[dict]:
    bundle = registry.load_active_bundle(db)
    if bundle is None:
        return []
    pipe, names = bundle["pipeline"], bundle["feature_names"]
    out = []
    for k in RISK_CHECKPOINTS:
        try:
            fd = build_feature_frame(frames=frames, student_ids=[sid], cutoff_seq=k,
                                     attend_cutoff_week=SEQ_TO_WEEK[k])
            if fd.X.empty:
                continue
            proba = pipe.predict_proba(fd.X[names])[0]
            out.append({"sequence": k, "week": SEQ_TO_WEEK[k],
                        "risk_probability": round(float(proba[2]), 3)})
        except Exception:
            continue
    return out
