"""ML lifecycle tables: model versions, experiments, predictions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ModelVersion(Base, TimestampMixin):
    """A trained, versioned model the backend can serve predictions from."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. "risk-xgboost"
    version: Mapped[str] = mapped_column(String(40), nullable=False)  # semantic/hash
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(40), nullable=False)
    training_dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    artifact_path: Mapped[Optional[str]] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(24), default="archived", nullable=False)


class Experiment(Base, TimestampMixin):
    """A single training run recorded for reproducibility and comparison."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_set: Mapped[str] = mapped_column(String(40), nullable=False)  # baseline|engineered
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)


class Prediction(Base, TimestampMixin):
    """A stored risk prediction, traceable to the model version that made it."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"), index=True
    )
    risk_label: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[Optional[dict]] = mapped_column(JSONB)  # per-class probs
    features: Mapped[Optional[dict]] = mapped_column(JSONB)  # feature snapshot
    shap_values: Mapped[Optional[dict]] = mapped_column(JSONB)  # explanation
    explanation: Mapped[Optional[str]] = mapped_column(Text)  # NL explanation
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
