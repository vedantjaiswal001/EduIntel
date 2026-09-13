# ML Methodology

## Problem framing

EduIntel predicts **end-of-term risk** as an early-warning task: given signals
available part-way through the term, estimate whether a student will finish at
LOW / MEDIUM / HIGH risk. The target is derived from each student's mean final
grade (`<50 → HIGH`, `50–65 → MEDIUM`, `≥65 → LOW`). The final exam carries 50%
of the grade and is **excluded** from the feature window, so the task is
genuinely hard and cannot be trivially solved.

## Feature engineering

16 features are computed **only from the feature window** (assessments with
sequence ≤ 7 — the final exam is sequence 8 — and attendance up to week 12):

| Group | Features |
|------|----------|
| Base | `attendance_pct`, `quiz_avg`, `assignment_avg`, `midterm_avg`, `prev_gpa`, `num_courses`, `missed_assignments` |
| Engineered | `rolling_mean_score`, `score_slope`, `attendance_slope`, `assignment_consistency`, `performance_volatility`, `recent_performance_delta`, `topic_weakness_score`, `submission_delay_mean` |

Slopes are computed per student-course (removing the course-difficulty confound)
then averaged. `topic_weakness_score` is the mean of a student's three weakest
topic masteries.

## Leakage prevention

See [leakage-prevention.md](leakage-prevention.md). In short: the final exam and
the final grade are never features; preprocessing (median imputation, scaling)
is fit inside a scikit-learn `Pipeline` on the **training fold only**; the
temporal window is enforced in code and covered by a unit test that proves
changing the excluded final exam leaves every feature identical.

## Validation strategy

- **Stratified train/test split** (80/20) preserving the class balance.
- **Stratified 5-fold cross-validation** on the training split for model
  selection, reported with a 95% confidence interval.
- For a multi-cohort production deployment the correct protocol is
  **chronological** (train on past cohorts, predict the current one); the
  feature-window design already respects temporal ordering within a term.

## Class imbalance

Classes are imbalanced (LOW 54% / MEDIUM 26% / HIGH 19%). Rather than resampling,
every model is fit with **balanced sample weights** (`compute_sample_weight`),
applied uniformly across Logistic Regression, Random Forest and XGBoost so the
comparison is fair. HIGH (the actionable minority) is treated as the positive
class throughout.

## Model comparison

Three models are compared on identical features and weighting. Metrics are the
full suite required for an intervention system: accuracy, per-class and macro
precision/recall/F1, ROC-AUC (OvR), PR-AUC, confusion matrix, and calibration.
See [experiment-report.md](experiment-report.md) for the numbers.

## Model selection — intervention-aware

Accuracy alone is the wrong objective: a HIGH-risk student wrongly called
LOW-risk is far costlier than a false alarm. The selection score is
`0.5 · HIGH-recall + 0.5 · macro-F1`, and the false-negative analysis
(`high_missed_as_low`) is tracked explicitly. On the held-out test set **no
model misclassified any HIGH-risk student as LOW** — HIGH is only ever confused
with the adjacent MEDIUM class.

## Calibration

Predicted HIGH-risk probabilities are evaluated with the Brier score and a
reliability curve, and compared against a sigmoid-calibrated variant. Because
instructors act on these probabilities, calibration is a first-class metric, not
an afterthought.

## Ablation & tuning

- **Ablation**: the same model is trained on the baseline vs the engineered
  feature set to measure whether engineering actually helps.
- **Optuna**: XGBoost hyperparameters are tuned (TPE sampler) and compared with
  the default configuration. Reported honestly even when tuning does not help.

## Experiment tracking & versioning

Every run is written to the `experiments` table (model, feature set,
hyperparameters, metrics, seed). The selected model is saved as a joblib bundle
and registered in `model_versions` with `status = active`; the backend serves
predictions from the active version, and every stored `prediction` references
the `model_version_id` that produced it — full lineage from prediction to model.
Runs are also logged to MLflow when `EDUINTEL_MLFLOW=1`.
