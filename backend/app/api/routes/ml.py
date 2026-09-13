"""ML Model Center & Experiment Tracking endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.ml import Experiment, ModelVersion

router = APIRouter(tags=["ml"])


@router.get("/models")
def list_models(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(ModelVersion).order_by(ModelVersion.created_at.desc())).scalars().all()
    return [_model_dict(m) for m in rows]


@router.get("/models/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db)) -> dict:
    m = db.get(ModelVersion, model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    return _model_dict(m, full=True)


@router.get("/experiments")
def list_experiments(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Experiment).order_by(Experiment.created_at.desc())).scalars().all()
    return [_exp_dict(e) for e in rows]


@router.get("/experiments/{exp_id}")
def get_experiment(exp_id: int, db: Session = Depends(get_db)) -> dict:
    e = db.get(Experiment, exp_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _exp_dict(e, full=True)


def _model_dict(m: ModelVersion, full: bool = False) -> dict:
    d = {
        "id": m.id, "name": m.name, "version": m.version, "model_type": m.model_type,
        "feature_version": m.feature_version, "dataset_version": m.training_dataset_version,
        "status": m.status, "created_at": m.created_at,
        "metrics_summary": _metrics_summary(m.metrics or {}),
    }
    if full:
        d["metrics"] = m.metrics
        d["hyperparameters"] = m.hyperparameters
        d["artifact_path"] = m.artifact_path
    return d


def _exp_dict(e: Experiment, full: bool = False) -> dict:
    d = {
        "id": e.id, "name": e.name, "model_type": e.model_type,
        "dataset_version": e.dataset_version, "feature_set": e.feature_set,
        "created_at": e.created_at, "seed": e.random_seed,
        "metrics_summary": _metrics_summary(e.metrics or {}),
    }
    if full:
        d["metrics"] = e.metrics
        d["hyperparameters"] = e.hyperparameters
        d["notes"] = e.notes
    return d


def _metrics_summary(m: dict) -> dict:
    fn = (m or {}).get("false_negative_analysis", {})
    return {
        "f1_macro": m.get("f1_macro"),
        "roc_auc_ovr_macro": m.get("roc_auc_ovr_macro"),
        "high_recall": fn.get("high_recall"),
        "accuracy": m.get("accuracy"),
    }
