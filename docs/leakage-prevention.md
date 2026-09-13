# How EduIntel prevents data leakage

Data leakage — when information unavailable at prediction time sneaks into
training — is the most common way education risk models produce impressive but
useless metrics. EduIntel guards against it in four ways.

## 1. Target leakage

The prediction target is derived from the **final grade**, which is dominated by
the **final exam (50% weight)**. Neither the final exam result nor the final
grade is ever used as a feature. Features come only from earlier assessments
(quizzes, assignments, midterm) and attendance.

## 2. Future-information leakage (temporal window)

Features are computed strictly from the **feature window**: assessment sequences
≤ 7 (the final exam is sequence 8) and attendance up to week 12. Anything that
happens at or after the final is invisible to the feature builder
(`FEATURE_WINDOW_MAX_SEQ = 7`, `ATTEND_CUTOFF_WEEK = 12`). The risk *trajectory*
feature re-applies the model at earlier cutoffs using only data available by that
point in the term — never peeking ahead.

This is verified by a unit test (`tests/test_features.py::
test_no_leakage_final_exam_does_not_change_features`): it builds the feature
matrix twice — once with the final exam at 5% and once at 95% — and asserts every
one of the 16 features is byte-for-byte identical.

## 3. Preprocessing leakage

All preprocessing that learns parameters (median imputation, standardisation) is
wrapped in a scikit-learn `Pipeline` and fit **inside each cross-validation fold
and the training split only** — never on the full dataset. Test/validation rows
never influence the imputation medians or scaling statistics.

## 4. Train/test contamination

Splits are stratified and disjoint; cross-validation folds are generated with a
fixed seed. Balanced sample weights are computed **per fold** from that fold's
training labels, so no label information crosses the fold boundary.

## Why the metrics are believable

Because the heavily-weighted final exam is excluded and carries large independent
noise, the achievable ceiling is bounded: ROC-AUC lands around 0.95 and macro-F1
around 0.83 — strong but clearly imperfect, with a meaningful HIGH-risk recall of
~0.77. A suspiciously perfect score (AUC ≈ 0.99) would itself be evidence of
leakage; this design deliberately avoids it.
