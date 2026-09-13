"""Explainable AI for risk predictions using SHAP.

For every student the model's HIGH-risk score is decomposed into per-feature
SHAP contributions, and a natural-language explanation is produced. The
language is deliberately **associative, not causal** ("associated with", not
"caused by"), and every explanation notes that it supports rather than
replaces instructor judgement.

The explainer is model-agnostic: it uses SHAP's unified `Explainer`, which
selects an exact TreeExplainer for tree models and a LinearExplainer for
logistic regression, on the pipeline's preprocessed feature space.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.ml import registry
from app.ml.features import build_feature_frame
from app.models.ml import Prediction

logger = get_logger(__name__)

HIGH_IDX = 2

FEATURE_LABELS: Dict[str, str] = {
    "attendance_pct": "attendance",
    "quiz_avg": "quiz performance",
    "assignment_avg": "assignment performance",
    "midterm_avg": "midterm performance",
    "prev_gpa": "prior GPA",
    "num_courses": "course load",
    "missed_assignments": "missed assignments",
    "rolling_mean_score": "overall early-term scores",
    "score_slope": "score trend",
    "attendance_slope": "attendance trend",
    "assignment_consistency": "assignment consistency",
    "performance_volatility": "score volatility",
    "recent_performance_delta": "recent score change",
    "topic_weakness_score": "weak-topic mastery",
    "submission_delay_mean": "submission delays",
}

# How to phrase a feature when it is *increasing* predicted risk.
RISK_PHRASE: Dict[str, str] = {
    "attendance_pct": "below-average attendance",
    "quiz_avg": "low quiz performance",
    "assignment_avg": "low assignment performance",
    "midterm_avg": "a low midterm score",
    "prev_gpa": "a lower prior GPA",
    "num_courses": "a heavy course load",
    "missed_assignments": "missed assignments",
    "rolling_mean_score": "low overall early-term scores",
    "score_slope": "a declining score trend",
    "attendance_slope": "a declining attendance trend",
    "assignment_consistency": "inconsistent assignment performance",
    "performance_volatility": "volatile performance",
    "recent_performance_delta": "a recent drop in scores",
    "topic_weakness_score": "weak mastery of key topics",
    "submission_delay_mean": "late assignment submissions",
}


def _shap_high(pipeline, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Return (shap_values[n, features], base_values[n]) for the HIGH class."""
    import shap

    pre = pipeline[:-1]
    clf = pipeline.named_steps["clf"]
    Xt = pre.transform(X)
    Xt = np.asarray(Xt)

    # Background sample for linear/kernel maskers (small for speed).
    bg = shap.utils.sample(Xt, min(100, len(Xt)), random_state=42)
    try:
        explainer = shap.Explainer(clf, bg)
    except Exception:  # pragma: no cover - fallback
        explainer = shap.Explainer(clf.predict_proba, bg)
    expl = explainer(Xt)

    vals = np.asarray(expl.values)
    base = np.asarray(expl.base_values)

    if vals.ndim == 3:  # (n, features, classes)
        v = vals[:, :, HIGH_IDX]
        b = base[:, HIGH_IDX] if base.ndim == 2 else np.full(len(X), float(np.ravel(base)[HIGH_IDX]))
    else:  # (n, features) single output
        v = vals
        b = base if base.ndim == 1 else np.full(len(X), float(np.ravel(base)[0]))
    return v, b


def _describe(top_positive: List[dict]) -> List[str]:
    return [RISK_PHRASE.get(f["feature"], FEATURE_LABELS.get(f["feature"], f["feature"]))
            for f in top_positive]


def _nl_explanation(name: str, label: str, p_high: float, top_positive: List[dict]) -> str:
    phrases = _describe(top_positive[:3])
    if label == "LOW_RISK" or not phrases:
        return (
            f"{name} is estimated LOW risk (about {p_high*100:.0f}% modelled high-risk "
            f"probability). No strong risk factors dominate. This estimate is based on "
            f"observed associations and supports, but does not replace, instructor judgement."
        )
    if len(phrases) == 1:
        joined = phrases[0]
    else:
        joined = ", ".join(phrases[:-1]) + f", and {phrases[-1]}"
    band = "HIGH" if label == "HIGH_RISK" else "MEDIUM"
    return (
        f"{name}'s risk is estimated {band} (about {p_high*100:.0f}% modelled high-risk "
        f"probability). The estimate is most associated with {joined}. These are "
        f"associations observed in the data, not proven causes, and are intended to "
        f"support instructor judgement rather than replace it."
    )


def generate_explanations(db: Session, engine: Engine, top_k: int = 6) -> int:
    bundle = registry.load_active_bundle(db)
    if bundle is None:
        logger.warning("No active model; cannot generate explanations.")
        return 0
    pipe = bundle["pipeline"]
    names = bundle["feature_names"]

    data = build_feature_frame(engine)
    X = data.X[names]
    v, base = _shap_high(pipe, X)

    preds = {p.student_id: p for p in db.query(Prediction).all()}
    students = {s.id: s.name for s in _load_student_names(db)}

    updated = 0
    for i, sid in enumerate(X.index):
        pred = preds.get(sid)
        if pred is None:
            continue
        row_vals = X.iloc[i]
        contribs = []
        for j, f in enumerate(names):
            val = row_vals[f]
            contribs.append({
                "feature": f,
                "label": FEATURE_LABELS.get(f, f),
                "shap": round(float(v[i, j]), 4),
                "value": None if pd.isna(val) else round(float(val), 3),
            })
        contribs.sort(key=lambda c: c["shap"], reverse=True)
        top_positive = [c for c in contribs if c["shap"] > 0][:top_k]

        pred.shap_values = {
            "class": "HIGH_RISK",
            "base_value": round(float(base[i]), 4),
            "top_factors": contribs[:top_k],
        }
        pred.explanation = _nl_explanation(
            students.get(sid, sid), pred.risk_label, pred.risk_probability, top_positive
        )
        updated += 1

    db.commit()
    logger.info("Generated %d explanations", updated)
    return updated


def _load_student_names(db: Session):
    from app.models.academic import Student

    return db.query(Student).all()
