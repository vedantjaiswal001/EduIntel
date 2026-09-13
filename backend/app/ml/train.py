"""Student-risk training pipeline.

Orchestrates the full experiment:
  1. Build leakage-safe features + target.
  2. Stratified train/test split.
  3. Compare Logistic Regression, Random Forest, XGBoost (CV + held-out test).
  4. Ablation: baseline vs engineered features.
  5. Optuna hyperparameter optimisation for XGBoost.
  6. Calibration comparison (raw vs sigmoid-calibrated).
  7. Select the best model (intervention-aware criterion), register it, and
     batch-predict all students into the predictions table.

Every run is logged to the experiments table for reproducibility. Class
imbalance is handled uniformly with balanced sample weights.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.logging import get_logger
from app.ml import evaluation, registry, tracking
from app.ml.features import (
    BASELINE_FEATURES,
    ENGINEERED_FEATURES,
    FeatureData,
    build_feature_frame,
    feature_list,
)

logger = get_logger(__name__)

DATASET_VERSION = "synthetic-v1"
FEATURE_VERSION = "fe-v1"
MODEL_NAME = "risk-model"
HIGH = 2


def make_pipeline(kind: str, seed: int, params: dict | None = None) -> Pipeline:
    steps = [("impute", SimpleImputer(strategy="median"))]
    if kind == "logreg":
        steps.append(("scale", StandardScaler()))
        clf = LogisticRegression(max_iter=3000)
    elif kind == "rf":
        clf = RandomForestClassifier(random_state=seed, n_jobs=-1, **(params or {"n_estimators": 300}))
    elif kind == "xgb":
        base = dict(objective="multi:softprob", num_class=3, eval_metric="mlogloss",
                    random_state=seed, n_jobs=-1, tree_method="hist")
        base.update(params or dict(n_estimators=300, max_depth=4, learning_rate=0.1,
                                   subsample=0.9, colsample_bytree=0.9))
        clf = XGBClassifier(**base)
    else:
        raise ValueError(kind)
    steps.append(("clf", clf))
    return Pipeline(steps)


def _fit(pipe: Pipeline, X: pd.DataFrame, y: np.ndarray) -> Pipeline:
    """Fit with balanced sample weights (uniform imbalance handling)."""
    w = compute_sample_weight("balanced", y)
    pipe.fit(X, y, clf__sample_weight=w)
    return pipe


def cv_f1(kind: str, X: pd.DataFrame, y: np.ndarray, seed: int, k: int = 5,
          params: dict | None = None) -> Tuple[float, float]:
    """Stratified k-fold macro-F1 with per-fold balanced weights."""
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    scores = []
    for tr, va in skf.split(X, y):
        pipe = make_pipeline(kind, seed, params)
        Xtr, Xva = X.iloc[tr], X.iloc[va]
        ytr, yva = y[tr], y[va]
        _fit(pipe, Xtr, ytr)
        scores.append(f1_score(yva, pipe.predict(Xva), average="macro"))
    return float(np.mean(scores)), float(np.std(scores))


def _ci95(mean: float, std: float, k: int) -> List[float]:
    half = 1.96 * std / np.sqrt(k)
    return [round(mean - half, 4), round(mean + half, 4)]


def train_and_eval(kind: str, X_tr, y_tr, X_te, y_te, seed: int,
                   params: dict | None = None) -> Tuple[Pipeline, Dict]:
    mean, std = cv_f1(kind, X_tr, y_tr, seed, params=params)
    pipe = make_pipeline(kind, seed, params)
    _fit(pipe, X_tr, y_tr)
    proba = pipe.predict_proba(X_te)
    y_pred = pipe.predict(X_te)
    metrics = evaluation.evaluate(y_te, y_pred, proba)
    metrics["cv_f1_mean"] = round(mean, 4)
    metrics["cv_f1_std"] = round(std, 4)
    metrics["cv_f1_ci95"] = _ci95(mean, std, 5)
    return pipe, metrics


def optuna_tune_xgb(X_tr, y_tr, seed: int, n_trials: int) -> dict:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: "optuna.Trial") -> float:
        params = dict(
            n_estimators=trial.suggest_int("n_estimators", 200, 600, step=50),
            max_depth=trial.suggest_int("max_depth", 3, 8),
            learning_rate=trial.suggest_float("learning_rate", 0.02, 0.3, log=True),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 10),
            reg_lambda=trial.suggest_float("reg_lambda", 0.0, 5.0),
        )
        mean, _ = cv_f1("xgb", X_tr, y_tr, seed, k=4, params=params)
        return mean

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params


def selection_score(metrics: Dict) -> float:
    """Intervention-aware selection: weight HIGH recall alongside macro-F1."""
    high_recall = metrics["false_negative_analysis"]["high_recall"]
    return 0.5 * high_recall + 0.5 * metrics["f1_macro"]


def run_training(db, engine, seed: int = 42, n_trials: int = 25) -> Dict:
    np.random.seed(seed)
    logger.info("Building features…")
    data: FeatureData = build_feature_frame(engine)
    X, y = data.X, data.y.to_numpy()
    logger.info("Feature matrix: %s | class dist: %s", X.shape,
                evaluation.class_distribution(y))

    X_eng = X[ENGINEERED_FEATURES]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_eng, y, test_size=0.2, stratify=y, random_state=seed
    )

    report: Dict = {
        "dataset_version": DATASET_VERSION,
        "feature_version": FEATURE_VERSION,
        "seed": seed,
        "n_samples": int(len(y)),
        "class_distribution": evaluation.class_distribution(y),
        "features": {"baseline": BASELINE_FEATURES, "engineered": ENGINEERED_FEATURES},
        "models": {},
    }

    # ---- 1) model comparison (engineered features) ----
    candidates: Dict[str, Tuple[Pipeline, Dict]] = {}
    for kind in ("logreg", "rf", "xgb"):
        pipe, metrics = train_and_eval(kind, X_tr, y_tr, X_te, y_te, seed)
        candidates[kind] = (pipe, metrics)
        report["models"][kind] = metrics
        tracking.log_experiment(
            db, name=f"{kind}-engineered", model_type=kind,
            dataset_version=DATASET_VERSION, feature_set="engineered",
            hyperparameters={}, metrics=_slim(metrics), seed=seed,
            notes="baseline model comparison on engineered features",
        )
        logger.info("%s: f1_macro=%.3f high_recall=%.3f roc_auc=%.3f", kind,
                    metrics["f1_macro"], metrics["false_negative_analysis"]["high_recall"],
                    metrics.get("roc_auc_ovr_macro") or -1)

    # ---- 2) ablation: XGB baseline vs engineered ----
    Xb_tr, Xb_te = X_tr[BASELINE_FEATURES], X_te[BASELINE_FEATURES]
    _, base_metrics = train_and_eval("xgb", Xb_tr, y_tr, Xb_te, y_te, seed)
    report["ablation"] = {
        "baseline": {"f1_macro": base_metrics["f1_macro"],
                     "high_recall": base_metrics["false_negative_analysis"]["high_recall"],
                     "roc_auc": base_metrics.get("roc_auc_ovr_macro")},
        "engineered": {"f1_macro": candidates["xgb"][1]["f1_macro"],
                       "high_recall": candidates["xgb"][1]["false_negative_analysis"]["high_recall"],
                       "roc_auc": candidates["xgb"][1].get("roc_auc_ovr_macro")},
    }
    report["ablation"]["f1_gain"] = round(
        report["ablation"]["engineered"]["f1_macro"] - report["ablation"]["baseline"]["f1_macro"], 4)
    tracking.log_experiment(
        db, name="xgb-baseline-features", model_type="xgb",
        dataset_version=DATASET_VERSION, feature_set="baseline",
        hyperparameters={}, metrics=_slim(base_metrics), seed=seed,
        notes="ablation: baseline feature set")

    # ---- 3) Optuna tuning of XGB ----
    logger.info("Optuna tuning XGB (%d trials)…", n_trials)
    best_params = optuna_tune_xgb(X_tr, y_tr, seed, n_trials)
    tuned_pipe, tuned_metrics = train_and_eval("xgb", X_tr, y_tr, X_te, y_te, seed,
                                               params=best_params)
    candidates["xgb-tuned"] = (tuned_pipe, tuned_metrics)
    report["models"]["xgb-tuned"] = tuned_metrics
    report["optuna"] = {
        "best_params": best_params,
        "baseline_xgb_f1": candidates["xgb"][1]["f1_macro"],
        "optimized_xgb_f1": tuned_metrics["f1_macro"],
        "f1_gain": round(tuned_metrics["f1_macro"] - candidates["xgb"][1]["f1_macro"], 4),
    }
    tracking.log_experiment(
        db, name="xgb-optuna", model_type="xgb",
        dataset_version=DATASET_VERSION, feature_set="engineered",
        hyperparameters=best_params, metrics=_slim(tuned_metrics), seed=seed,
        notes="Optuna-optimised XGBoost")

    # ---- 4) select best (intervention-aware) ----
    best_kind = max(candidates, key=lambda k: selection_score(candidates[k][1]))
    best_pipe, best_metrics = candidates[best_kind]
    report["selected_model"] = {"kind": best_kind,
                                "selection_score": round(selection_score(best_metrics), 4)}

    # ---- 5) calibration comparison (raw vs sigmoid) ----
    report["calibration_comparison"] = _calibration_compare(best_kind, best_params, X_tr, y_tr, X_te, y_te, seed)

    # ---- 6) register + persist ----
    version = registry.make_version(best_kind, FEATURE_VERSION, DATASET_VERSION)
    meta = {"kind": best_kind, "feature_set": "engineered",
            "labels": ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"],
            "selected_by": "0.5*high_recall + 0.5*f1_macro"}
    artifact = registry.save_bundle(best_pipe, ENGINEERED_FEATURES, meta, MODEL_NAME, version)
    mv = registry.register_model_version(
        db, name=MODEL_NAME, version=version, model_type=best_kind,
        feature_version=FEATURE_VERSION, dataset_version=DATASET_VERSION,
        metrics=_slim(best_metrics), hyperparameters=best_params if "xgb" in best_kind else {},
        artifact_path=artifact, make_active=True)
    report["model_version"] = {"id": mv.id, "version": version, "artifact": artifact}

    # ---- 7) batch predict all students into predictions table ----
    from app.ml.serving import batch_predict_and_store

    n_pred = batch_predict_and_store(db, engine, best_pipe, ENGINEERED_FEATURES, mv.id)
    report["predictions_stored"] = n_pred

    # ---- 8) SHAP explanations for every stored prediction ----
    try:
        from app.ml.explain import generate_explanations

        report["explanations_generated"] = generate_explanations(db, engine)
    except Exception as exc:  # pragma: no cover
        logger.warning("Explanation generation failed: %s", exc)
        report["explanations_generated"] = 0

    # save report for docs / Phase 14
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    with open(os.path.join(settings.MODEL_DIR, "training_report.json"), "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    return report


def _calibration_compare(kind, params, X_tr, y_tr, X_te, y_te, seed) -> Dict:
    raw = make_pipeline("xgb" if "xgb" in kind else kind, seed,
                        params if "xgb" in kind else None)
    _fit(raw, X_tr, y_tr)
    raw_brier = brier_score_loss((y_te == HIGH).astype(int), raw.predict_proba(X_te)[:, HIGH])
    try:
        # Note: sample_weight is not forwarded through a Pipeline base estimator
        # by CalibratedClassifierCV, so we calibrate without it (the base model
        # already handles imbalance via its own weighted fit above).
        calibrated = CalibratedClassifierCV(raw, method="sigmoid", cv=3)
        calibrated.fit(X_tr, y_tr)
        cal_brier = brier_score_loss((y_te == HIGH).astype(int),
                                     calibrated.predict_proba(X_te)[:, HIGH])
    except Exception as exc:  # pragma: no cover
        logger.warning("calibration failed: %s", exc)
        cal_brier = None
    return {"raw_brier_high": round(float(raw_brier), 4),
            "sigmoid_calibrated_brier_high": round(float(cal_brier), 4) if cal_brier else None}


def _slim(metrics: Dict) -> Dict:
    """Store a compact metrics subset in the DB (drop bulky arrays)."""
    keep = {k: v for k, v in metrics.items()
            if k not in ("confusion_matrix", "calibration")}
    keep["confusion_matrix"] = metrics.get("confusion_matrix")
    keep["brier_high"] = metrics.get("calibration", {}).get("brier_high")
    return keep
