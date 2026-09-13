"""Feature-engineering unit tests, including a leakage-exclusion test."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.features import (
    BASELINE_FEATURES,
    ENGINEERED_FEATURES,
    FEATURE_WINDOW_MAX_SEQ,
    build_feature_frame,
    grade_to_label,
)


def test_grade_to_label_boundaries():
    assert grade_to_label(49) == "HIGH_RISK"
    assert grade_to_label(50) == "MEDIUM_RISK"
    assert grade_to_label(64.9) == "MEDIUM_RISK"
    assert grade_to_label(65) == "LOW_RISK"
    assert grade_to_label(90) == "LOW_RISK"


def test_feature_window_excludes_final_exam():
    assert FEATURE_WINDOW_MAX_SEQ == 7  # the final exam is sequence 8


def _tiny_frames(final_exam_pct: float):
    """One student, one course; the final exam (seq 8) has the given percentage."""
    res = pd.DataFrame([
        # sequence, kind, percentage
        dict(student_id="S1", course_id="C1", sequence=1, kind="quiz", percentage=80, is_missing=False, submission_delay_hours=None),
        dict(student_id="S1", course_id="C1", sequence=2, kind="assignment", percentage=70, is_missing=False, submission_delay_hours=2.0),
        dict(student_id="S1", course_id="C1", sequence=3, kind="quiz", percentage=60, is_missing=False, submission_delay_hours=None),
        dict(student_id="S1", course_id="C1", sequence=5, kind="exam", percentage=50, is_missing=False, submission_delay_hours=None),
        dict(student_id="S1", course_id="C1", sequence=7, kind="assignment", percentage=40, is_missing=False, submission_delay_hours=1.0),
        dict(student_id="S1", course_id="C1", sequence=8, kind="exam", percentage=final_exam_pct, is_missing=False, submission_delay_hours=None),
    ])
    att = pd.DataFrame([dict(student_id="S1", course_id="C1", week=w, status="present") for w in range(1, 15)])
    mastery = pd.DataFrame([dict(student_id="S1", topic_id="C1-T01", mastery=0.5)])
    students = pd.DataFrame([dict(student_id="S1", prev_gpa=7.0)])
    enroll = pd.DataFrame([dict(student_id="S1", course_id="C1", final_grade=60.0)])
    return {"res": res, "att": att, "mastery": mastery, "students": students, "enroll": enroll}


def test_no_leakage_final_exam_does_not_change_features():
    """Changing the (excluded) final exam must not change any feature value."""
    a = build_feature_frame(frames=_tiny_frames(final_exam_pct=5))
    b = build_feature_frame(frames=_tiny_frames(final_exam_pct=95))
    # rolling mean uses only seq<=7 assessments -> mean(80,70,60,50,40) = 60
    assert abs(a.X.loc["S1", "rolling_mean_score"] - 60.0) < 1e-6
    # identical features regardless of the final exam score
    for col in ENGINEERED_FEATURES:
        va, vb = a.X.loc["S1", col], b.X.loc["S1", col]
        if pd.isna(va) and pd.isna(vb):
            continue
        assert abs(float(va) - float(vb)) < 1e-9, f"feature {col} leaked from final exam"


def test_feature_columns_present():
    fd = build_feature_frame(frames=_tiny_frames(50))
    assert set(BASELINE_FEATURES).issubset(set(fd.X.columns))
    assert "midterm_avg" in fd.X.columns
    assert fd.X.loc["S1", "midterm_avg"] == 50  # the seq-5 exam


def test_student_with_no_assessments_is_handled():
    frames = _tiny_frames(50)
    frames["res"] = frames["res"].iloc[0:0]  # empty assessments
    fd = build_feature_frame(frames=frames)
    # still produces a row; performance features are NaN, counts default to 0
    assert "S1" in fd.X.index
    assert fd.X.loc["S1", "missed_assignments"] == 0
