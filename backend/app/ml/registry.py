"""Model versioning and artifact management.

A trained model is saved as a joblib bundle (pipeline + feature list + label
mapping + metadata) and registered in the `model_versions` table. The backend
serves predictions from whichever version is marked `active`, so every stored
prediction is traceable to the exact model that produced it.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import List, Optional

import joblib
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ml import ModelVersion


def _short_hash(payload: str) -> str:
    return hashlib.sha1(payload.encode()).hexdigest()[:10]


def make_version(model_type: str, feature_version: str, dataset_version: str) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    h = _short_hash(f"{model_type}{feature_version}{dataset_version}{stamp}")
    return f"{stamp}-{h}"


def save_bundle(pipeline, feature_names: List[str], meta: dict, name: str, version: str) -> str:
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    # Store an absolute path so the model loads regardless of the process CWD
    # (training may run from the repo root, the API from backend/ or /app).
    path = os.path.abspath(os.path.join(settings.MODEL_DIR, f"{name}-{version}.joblib"))
    joblib.dump(
        {"pipeline": pipeline, "feature_names": feature_names, "meta": meta}, path
    )
    return path


def load_bundle(path: str) -> dict:
    return joblib.load(path)


def register_model_version(
    db: Session,
    *,
    name: str,
    version: str,
    model_type: str,
    feature_version: str,
    dataset_version: str,
    metrics: dict,
    hyperparameters: dict,
    artifact_path: str,
    make_active: bool = True,
) -> ModelVersion:
    if make_active:
        db.execute(
            update(ModelVersion)
            .where(ModelVersion.name == name, ModelVersion.status == "active")
            .values(status="archived")
        )
    mv = ModelVersion(
        name=name,
        version=version,
        model_type=model_type,
        feature_version=feature_version,
        training_dataset_version=dataset_version,
        metrics=metrics,
        hyperparameters=hyperparameters,
        artifact_path=artifact_path,
        status="active" if make_active else "archived",
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return mv


def get_active_model_version(db: Session, name: str = "risk-model") -> Optional[ModelVersion]:
    return db.execute(
        select(ModelVersion)
        .where(ModelVersion.name == name, ModelVersion.status == "active")
        .order_by(ModelVersion.created_at.desc())
    ).scalars().first()


def load_active_bundle(db: Session, name: str = "risk-model") -> Optional[dict]:
    mv = get_active_model_version(db, name)
    if mv is None or not mv.artifact_path:
        return None
    path = mv.artifact_path
    if not os.path.exists(path):
        # Fall back to resolving the basename inside the configured model dir
        # (handles a model trained in a different working directory).
        alt = os.path.abspath(os.path.join(settings.MODEL_DIR, os.path.basename(path)))
        if os.path.exists(alt):
            path = alt
        else:
            return None
    bundle = load_bundle(path)
    bundle["version_id"] = mv.id
    bundle["version"] = mv.version
    return bundle
