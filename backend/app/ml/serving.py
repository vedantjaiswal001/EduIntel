"""Risk prediction serving.

Batch prediction stores one row per student in the `predictions` table (traceable
to the model version), which powers the dashboard risk distribution and fast
Student-360 reads. Live prediction is available for what-if scenarios.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.ml.features import INT_TO_LABEL, build_feature_frame
from app.models.ml import ModelVersion, Prediction

HIGH_IDX = 2


def _predict_df(pipe, X: pd.DataFrame) -> pd.DataFrame:
    proba = pipe.predict_proba(X)
    pred = proba.argmax(axis=1)
    out = pd.DataFrame(index=X.index)
    out["label"] = [INT_TO_LABEL[i] for i in pred]
    out["p_high"] = proba[:, HIGH_IDX]
    out["probabilities"] = [
        {INT_TO_LABEL[i]: round(float(proba[r, i]), 4) for i in range(proba.shape[1])}
        for r in range(len(X))
    ]
    return out


def batch_predict_and_store(
    db: Session, engine: Engine, pipe, feature_names: List[str], model_version_id: int
) -> int:
    data = build_feature_frame(engine)
    X = data.X[feature_names]
    preds = _predict_df(pipe, X)
    now = datetime.utcnow()

    # Replace previous predictions (single active snapshot).
    db.query(Prediction).delete()
    db.commit()

    rows = []
    for sid, row in preds.iterrows():
        feat_snapshot = {k: (None if pd.isna(v) else round(float(v), 4))
                         for k, v in data.X.loc[sid, feature_names].items()}
        rows.append(Prediction(
            student_id=sid,
            model_version_id=model_version_id,
            risk_label=row["label"],
            risk_probability=float(row["p_high"]),
            probabilities=row["probabilities"],
            features=feat_snapshot,
            predicted_at=now,
        ))
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def get_student_prediction(db: Session, student_id: str) -> Optional[Prediction]:
    return db.execute(
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.predicted_at.desc())
    ).scalars().first()


def get_at_risk_students(db: Session, limit: int = 50, label: str = "HIGH_RISK") -> List[Prediction]:
    return db.execute(
        select(Prediction)
        .where(Prediction.risk_label == label)
        .order_by(Prediction.risk_probability.desc())
        .limit(limit)
    ).scalars().all()


def predict_live(bundle: dict, features_row: Dict[str, float]) -> Dict:
    """Predict from an explicit feature dict (used for what-if scenarios)."""
    pipe = bundle["pipeline"]
    names = bundle["feature_names"]
    X = pd.DataFrame([{k: features_row.get(k, np.nan) for k in names}])
    proba = pipe.predict_proba(X)[0]
    pred = int(proba.argmax())
    return {
        "risk_label": INT_TO_LABEL[pred],
        "risk_probability": float(proba[HIGH_IDX]),
        "probabilities": {INT_TO_LABEL[i]: float(proba[i]) for i in range(len(proba))},
    }
