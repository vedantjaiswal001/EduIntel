"""Experiment tracking.

Every training run is recorded in the `experiments` table (model type, dataset
version, feature set, hyperparameters, metrics, seed). If MLflow is installed
and EDUINTEL_MLFLOW=1, runs are also logged there — but the DB table is the
always-on source of truth so the platform is self-contained.
"""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ml import Experiment

logger = get_logger(__name__)


def log_experiment(
    db: Session,
    *,
    name: str,
    model_type: str,
    dataset_version: str,
    feature_set: str,
    hyperparameters: dict,
    metrics: dict,
    seed: int,
    notes: Optional[str] = None,
) -> Experiment:
    exp = Experiment(
        name=name,
        model_type=model_type,
        dataset_version=dataset_version,
        feature_set=feature_set,
        hyperparameters=hyperparameters,
        metrics=metrics,
        random_seed=seed,
        notes=notes,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)

    if os.getenv("EDUINTEL_MLFLOW") == "1":
        _log_mlflow(name, model_type, feature_set, hyperparameters, metrics)
    return exp


def _log_mlflow(name, model_type, feature_set, hyperparameters, metrics) -> None:  # pragma: no cover
    try:
        import mlflow

        with mlflow.start_run(run_name=name):
            mlflow.log_params({"model_type": model_type, "feature_set": feature_set,
                               **{k: v for k, v in hyperparameters.items()}})
            flat = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
            mlflow.log_metrics(flat)
    except Exception as exc:
        logger.warning("MLflow logging skipped: %s", exc)
