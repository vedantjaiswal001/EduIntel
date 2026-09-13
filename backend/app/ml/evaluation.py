"""Model evaluation.

Produces the full metric suite required for an intervention system, with
explicit attention to false negatives (a HIGH-risk student wrongly called
LOW-risk is the costliest error) and calibration (probabilities must be
trustworthy if instructors act on them).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.ml.features import INT_TO_LABEL, RISK_LABELS

HIGH = 2  # int code for HIGH_RISK


def _one_hot(y: np.ndarray, n: int = 3) -> np.ndarray:
    oh = np.zeros((len(y), n))
    oh[np.arange(len(y)), y] = 1
    return oh


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray) -> Dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    oh = _one_hot(y_true)

    metrics: Dict = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }
    try:
        metrics["roc_auc_ovr_macro"] = float(
            roc_auc_score(y_true, proba, multi_class="ovr", average="macro")
        )
    except ValueError:
        metrics["roc_auc_ovr_macro"] = None
    try:
        metrics["pr_auc_macro"] = float(average_precision_score(oh, proba, average="macro"))
    except ValueError:
        metrics["pr_auc_macro"] = None

    # per-class precision/recall/f1
    per_class = {}
    p = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
    r = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
    fs = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
    for i, label in INT_TO_LABEL.items():
        per_class[label] = {"precision": float(p[i]), "recall": float(r[i]), "f1": float(fs[i])}
    metrics["per_class"] = per_class

    # confusion matrix (rows = true, cols = pred), labelled
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    metrics["confusion_matrix"] = {"labels": RISK_LABELS, "matrix": cm.tolist()}

    # ---- false-negative analysis for HIGH risk ----
    n_high = int((y_true == HIGH).sum())
    high_mask = y_true == HIGH
    high_recall = float(recall_score(y_true, y_pred, labels=[HIGH], average="macro", zero_division=0))
    fn_high = int(((y_true == HIGH) & (y_pred != HIGH)).sum())
    high_as_low = int(((y_true == HIGH) & (y_pred == 0)).sum())
    metrics["false_negative_analysis"] = {
        "n_high_risk": n_high,
        "high_recall": high_recall,
        "high_false_negatives": fn_high,
        "high_missed_as_low": high_as_low,
        "note": "HIGH-risk students predicted LOW are the costliest errors; "
                "high_recall and high_missed_as_low are the key monitoring metrics.",
    }

    # ---- calibration of the HIGH-risk probability ----
    p_high = proba[:, HIGH]
    y_high = (y_true == HIGH).astype(int)
    metrics["calibration"] = {
        "brier_high": float(brier_score_loss(y_high, p_high)),
        "reliability": _reliability(y_high, p_high),
    }
    return metrics


def _reliability(y_high: np.ndarray, p_high: np.ndarray, bins: int = 10) -> List[dict]:
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for i in range(bins):
        m = (p_high >= edges[i]) & (p_high < edges[i + 1] if i < bins - 1 else p_high <= edges[i + 1])
        if m.sum() == 0:
            continue
        out.append({
            "bin": round((edges[i] + edges[i + 1]) / 2, 3),
            "mean_pred": round(float(p_high[m].mean()), 3),
            "frac_positive": round(float(y_high[m].mean()), 3),
            "count": int(m.sum()),
        })
    return out


def class_distribution(y: np.ndarray) -> Dict[str, int]:
    y = np.asarray(y)
    return {INT_TO_LABEL[i]: int((y == i).sum()) for i in (0, 1, 2)}
