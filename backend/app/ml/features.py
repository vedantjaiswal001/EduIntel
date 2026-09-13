"""Leakage-safe feature engineering for student-risk prediction.

Design (early-warning framing):
  * TARGET  – derived from each student's mean final grade (which is dominated
    by the final exam). Three classes: LOW_RISK / MEDIUM_RISK / HIGH_RISK.
  * FEATURES – computed ONLY from the feature window: assessments with
    sequence <= FEATURE_WINDOW_MAX_SEQ (excludes the final exam) and attendance
    up to ATTEND_CUTOFF_WEEK. The final exam and the target-derived final grade
    are never used as inputs.

Why this is not leakage: early assessments are legitimate signals available
before the outcome; they are *predictors*, not the label. Leakage would be
using the final exam, the final grade, or any post-outcome value as a feature —
which we explicitly exclude. Preprocessing that learns parameters (imputation,
scaling) is fit on the training split only, inside the model Pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

# Feature-window boundaries (exclude the final exam at sequence 8, week 14).
FEATURE_WINDOW_MAX_SEQ = 7
ATTEND_CUTOFF_WEEK = 12
MIDTERM_SEQ = 5
# Assessment sequence -> term week (matches the synthetic generator schedule).
SEQ_TO_WEEK = {1: 3, 2: 4, 3: 6, 4: 8, 5: 9, 6: 10, 7: 11, 8: 14}

RISK_LABELS = ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]
# Ordered so index encodes severity (0=LOW..2=HIGH); HIGH is the positive class.
LABEL_TO_INT = {"LOW_RISK": 0, "MEDIUM_RISK": 1, "HIGH_RISK": 2}
INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}

BASELINE_FEATURES = [
    "attendance_pct",
    "quiz_avg",
    "assignment_avg",
    "midterm_avg",
    "prev_gpa",
    "num_courses",
    "missed_assignments",
]
ENGINEERED_FEATURES = BASELINE_FEATURES + [
    "rolling_mean_score",
    "score_slope",
    "attendance_slope",
    "assignment_consistency",
    "performance_volatility",
    "recent_performance_delta",
    "topic_weakness_score",
    "submission_delay_mean",
]


@dataclass
class FeatureData:
    X: pd.DataFrame            # index = student_id, columns = ENGINEERED_FEATURES
    y: pd.Series               # int-encoded labels aligned to X
    y_label: pd.Series         # string labels
    final_avg: pd.Series       # mean final grade (for reference/analysis only)


def grade_to_label(final_avg: float) -> str:
    if final_avg < 50:
        return "HIGH_RISK"
    if final_avg < 65:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.ptp(x) == 0:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def _load_frames(engine: Engine) -> dict:
    res = pd.read_sql(
        "SELECT ar.student_id, a.course_id, a.sequence, a.kind, ar.percentage, "
        "ar.is_missing, ar.submission_delay_hours "
        "FROM assessment_results ar JOIN assessments a ON a.id = ar.assessment_id",
        engine,
    )
    att = pd.read_sql("SELECT student_id, course_id, week, status FROM attendance", engine)
    mastery = pd.read_sql("SELECT student_id, topic_id, mastery FROM student_topic_mastery", engine)
    students = pd.read_sql("SELECT id AS student_id, prev_gpa FROM students", engine)
    enroll = pd.read_sql("SELECT student_id, course_id, final_grade FROM enrollments", engine)
    return {"res": res, "att": att, "mastery": mastery, "students": students, "enroll": enroll}


def build_feature_frame(
    engine: Optional[Engine] = None,
    student_ids: Optional[List[str]] = None,
    frames: Optional[dict] = None,
    cutoff_seq: int = FEATURE_WINDOW_MAX_SEQ,
    attend_cutoff_week: int = ATTEND_CUTOFF_WEEK,
) -> FeatureData:
    """Build the full feature matrix + target.

    Args:
        engine: DB engine (ignored if `frames` is provided).
        student_ids: restrict to these students.
        frames: preloaded table frames (to avoid repeated DB loads, e.g. when
            computing a risk trajectory across multiple cutoffs).
        cutoff_seq / attend_cutoff_week: feature-window boundaries. Lowering
            them simulates "what was known by this point in the term" for the
            risk trajectory. The final exam (seq 8) is always excluded.
    """
    f = frames if frames is not None else _load_frames(engine)
    res, att, mastery = f["res"], f["att"], f["mastery"]
    students, enroll = f["students"], f["enroll"]

    if student_ids is not None:
        sset = set(student_ids)
        res = res[res.student_id.isin(sset)]
        att = att[att.student_id.isin(sset)]
        mastery = mastery[mastery.student_id.isin(sset)]
        students = students[students.student_id.isin(sset)]
        enroll = enroll[enroll.student_id.isin(sset)]

    # ---- feature window (exclude final exam + late attendance) ----
    cutoff_seq = min(cutoff_seq, FEATURE_WINDOW_MAX_SEQ)  # never include the final
    win = res[res["sequence"] <= cutoff_seq].copy()
    att_win = att[att["week"] <= attend_cutoff_week].copy()
    att_win["w"] = att_win["status"].map({"present": 1.0, "late": 0.5, "absent": 0.0})

    feats = pd.DataFrame({"student_id": students["student_id"]}).set_index("student_id")

    # attendance %
    feats["attendance_pct"] = att_win.groupby("student_id")["w"].mean() * 100

    # per-kind averages
    quiz = win[win.kind == "quiz"].groupby("student_id")["percentage"].mean()
    asg = win[win.kind == "assignment"].groupby("student_id")["percentage"].mean()
    mid = win[win.sequence == MIDTERM_SEQ].groupby("student_id")["percentage"].mean()
    feats["quiz_avg"] = quiz
    feats["assignment_avg"] = asg
    feats["midterm_avg"] = mid

    # prev gpa, num courses
    feats["prev_gpa"] = students.set_index("student_id")["prev_gpa"]
    feats["num_courses"] = enroll.groupby("student_id")["course_id"].nunique()

    # missed assignments (window)
    missed = win[(win.kind == "assignment") & (win.is_missing)].groupby("student_id").size()
    feats["missed_assignments"] = missed

    # rolling mean + volatility over all window assessments
    feats["rolling_mean_score"] = win.groupby("student_id")["percentage"].mean()
    feats["performance_volatility"] = win.groupby("student_id")["percentage"].std()

    # score slope: per student-course OLS over quiz/exam %, averaged
    qe = win[win.kind.isin(["quiz", "exam"])]
    if len(qe):
        feats["score_slope"] = (
            qe.groupby(["student_id", "course_id"])
            .apply(lambda g: _slope(g["sequence"].to_numpy(float), g["percentage"].to_numpy(float)),
                   include_groups=False)
            .groupby(level=0).mean()
        )

    # attendance slope: per student-course weekly rate OLS, averaged
    weekly = att_win.groupby(["student_id", "course_id", "week"])["w"].mean().reset_index()
    if len(weekly):
        feats["attendance_slope"] = (
            weekly.groupby(["student_id", "course_id"])
            .apply(lambda g: _slope(g["week"].to_numpy(float), g["w"].to_numpy(float)),
                   include_groups=False)
            .groupby(level=0).mean()
        )

    # assignment consistency = 100 - std(assignment %); higher = steadier
    asg_std = win[win.kind == "assignment"].groupby("student_id")["percentage"].std()
    feats["assignment_consistency"] = (100 - asg_std).clip(lower=0)

    # recent performance delta: (last-2 mean) - (first-2 mean) per course, averaged
    def _delta(g: pd.DataFrame) -> float:
        g = g.sort_values("sequence")
        vals = g["percentage"].to_numpy(float)
        if len(vals) < 2:
            return 0.0
        k = max(1, len(vals) // 2)
        return float(vals[-k:].mean() - vals[:k].mean())

    if len(win):
        feats["recent_performance_delta"] = (
            win.groupby(["student_id", "course_id"]).apply(_delta, include_groups=False)
            .groupby(level=0).mean()
        )

    # topic weakness: mean of the student's 3 weakest topic masteries (0-100)
    def _weak(s: pd.Series) -> float:
        return float(np.sort(s.to_numpy())[:3].mean() * 100)

    tw = mastery.groupby("student_id")["mastery"].apply(_weak)
    feats["topic_weakness_score"] = tw

    # submission delay mean over submitted assignments
    sd = (
        win[(win.kind == "assignment") & (win.submission_delay_hours.notna())]
        .groupby("student_id")["submission_delay_hours"].mean()
    )
    feats["submission_delay_mean"] = sd

    # ---- target from mean final grade (never used as a feature) ----
    final_avg = enroll.groupby("student_id")["final_grade"].mean()
    y_label = final_avg.map(grade_to_label)

    # Align, keep only students that have both features and a target.
    feats = feats.reindex(columns=ENGINEERED_FEATURES)
    common = feats.index.intersection(y_label.dropna().index)
    feats = feats.loc[common]
    y_label = y_label.loc[common]
    final_avg = final_avg.loc[common]

    # Note: missing feature values are left as NaN and imputed inside the model
    # Pipeline (fit on train only). num_courses/missed default to 0 sensibly.
    feats["missed_assignments"] = feats["missed_assignments"].fillna(0)
    feats["num_courses"] = feats["num_courses"].fillna(0)

    y = y_label.map(LABEL_TO_INT).astype(int)
    return FeatureData(X=feats, y=y, y_label=y_label, final_avg=final_avg)


def feature_list(feature_set: str) -> List[str]:
    return BASELINE_FEATURES if feature_set == "baseline" else ENGINEERED_FEATURES
