"""Model-evaluation unit tests."""
from __future__ import annotations

import numpy as np

from app.analytics.course_health import COMPONENT_WEIGHTS
from app.ml.evaluation import class_distribution, evaluate


def test_course_health_weights_sum_to_one():
    assert abs(sum(COMPONENT_WEIGHTS.values()) - 1.0) < 1e-9


def test_evaluate_metric_shapes_and_false_negatives():
    rng = np.random.default_rng(0)
    y_true = np.array([0, 0, 1, 1, 2, 2, 2, 0, 1, 2])
    # deliberately mislabel one HIGH (2) as LOW (0) to exercise FN analysis
    y_pred = np.array([0, 0, 1, 1, 2, 2, 0, 0, 1, 2])
    proba = np.zeros((len(y_true), 3))
    for i, c in enumerate(y_pred):
        proba[i, c] = 0.7
        proba[i, (c + 1) % 3] = 0.3
    m = evaluate(y_true, y_pred, proba)
    assert 0.0 <= m["accuracy"] <= 1.0
    assert set(m["per_class"].keys()) == {"LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"}
    assert m["confusion_matrix"]["matrix"]  # 3x3
    fn = m["false_negative_analysis"]
    assert fn["n_high_risk"] == 4
    assert fn["high_missed_as_low"] == 1  # the one HIGH predicted LOW
    assert "calibration" in m


def test_class_distribution():
    d = class_distribution(np.array([0, 0, 1, 2, 2, 2]))
    assert d == {"LOW_RISK": 2, "MEDIUM_RISK": 1, "HIGH_RISK": 3}
