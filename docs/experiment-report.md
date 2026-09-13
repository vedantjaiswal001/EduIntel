# ML Experiment Report

_Dataset: `synthetic-v1`, seed 42, 1,000 students. Reproduce with_
`python scripts/train.py --seed 42 --trials 25`. _All figures are from the
held-out 20% test set unless noted; a fresh `models/training_report.json` is
written on every run._

## Dataset

| Class | Count | Share |
|------|------:|------:|
| LOW_RISK | 544 | 54.4% |
| MEDIUM_RISK | 262 | 26.2% |
| HIGH_RISK | 194 | 19.4% |

## Model comparison (held-out test)

| Model | Accuracy | Macro-F1 | ROC-AUC (OvR) | PR-AUC | HIGH recall | HIGH→LOW errors | CV F1 95% CI |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Logistic Regression** ⭐ | 0.850 | **0.827** | 0.962 | 0.893 | 0.769 | **0** | [0.854, 0.881] |
| Random Forest | 0.840 | 0.800 | 0.956 | 0.875 | 0.692 | 0 | [0.846, 0.871] |
| XGBoost | 0.830 | 0.791 | 0.949 | 0.863 | 0.718 | 0 | [0.857, 0.869] |
| XGBoost (Optuna) | 0.830 | 0.791 | 0.953 | 0.870 | 0.718 | 0 | [0.857, 0.884] |

⭐ selected by the intervention-aware score `0.5·HIGH-recall + 0.5·F1 = 0.798`.
Logistic Regression winning is a useful reminder that a well-regularised linear
model can beat gradient boosting on tabular data with strong linear signal.

### Per-class F1 (Logistic Regression)

| Class | F1 |
|------|:--:|
| LOW_RISK | 0.923 |
| MEDIUM_RISK | 0.746 |
| HIGH_RISK | 0.811 |

### Confusion matrix (Logistic Regression, rows = actual, cols = predicted)

|               | LOW | MEDIUM | HIGH |
|---------------|:---:|:------:|:----:|
| **LOW**       | 96  | 13     | 0    |
| **MEDIUM**    | 3   | 44     | 5    |
| **HIGH**      | 0   | 9      | 30   |

**Key result:** the bottom-left cell is **0** — no HIGH-risk student was
predicted LOW-risk. HIGH is only confused with the adjacent MEDIUM class, which
is the desirable failure mode for an early-warning system (a missed high-risk
student still surfaces as medium risk rather than disappearing).

## Ablation — baseline vs engineered features (XGBoost)

| Feature set | Macro-F1 | ROC-AUC |
|------|:--:|:--:|
| Baseline (7 features) | 0.767 | 0.933 |
| Engineered (16 features) | 0.791 | 0.949 |
| **Gain** | **+0.024** | **+0.016** |

Feature engineering delivers a real, measurable lift.

## Hyperparameter optimisation — Optuna (XGBoost)

Best params: `n_estimators=550, max_depth=4, learning_rate=0.026, subsample=0.87,
colsample_bytree=0.78, min_child_weight=2, reg_lambda=2.48`.

| | Macro-F1 |
|--|:--:|
| Default XGBoost | 0.791 |
| Optuna-tuned | 0.791 |
| Gain | +0.000 |

Reported honestly: on this dataset the default XGBoost is already near-optimal
and tuning did not improve held-out F1 (it slightly improved ROC-AUC and PR-AUC).
This is a genuine, common outcome and is not hidden.

## Calibration (HIGH-risk probability)

| | Brier score (lower is better) |
|--|:--:|
| Raw model | 0.054 |
| Sigmoid-calibrated | 0.060 |

The raw model is already well-calibrated; sigmoid calibration did not help here.

## Error analysis

The residual errors concentrate on the MEDIUM class (the fuzzy middle band),
which is expected: LOW and HIGH are well separated, while MEDIUM borders both.
For intervention triage this is acceptable — the costly LOW/HIGH confusion does
not occur.
