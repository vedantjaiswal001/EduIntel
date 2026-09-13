#!/usr/bin/env python3
"""Train the student-risk model: comparison, ablation, Optuna, calibration,
registration and batch prediction. Reproducible via --seed.

Usage:
    python scripts/train.py --seed 42 --trials 25
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.ml.train import run_training  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trials", type=int, default=25)
    args = ap.parse_args()

    configure_logging()
    with SessionLocal() as db:
        report = run_training(db, engine, seed=args.seed, n_trials=args.trials)

    # Concise console summary.
    print("\n================ TRAINING SUMMARY ================")
    print(f"Samples: {report['n_samples']} | classes: {report['class_distribution']}")
    print("\nModel comparison (held-out test):")
    print(f"{'model':<12}{'f1_macro':>10}{'roc_auc':>10}{'HIGH_recall':>13}{'cv_f1(95% CI)':>22}")
    for name, m in report["models"].items():
        fn = m["false_negative_analysis"]
        ci = m.get("cv_f1_ci95")
        ci_s = f"[{ci[0]:.3f},{ci[1]:.3f}]" if ci else "-"
        roc = m.get("roc_auc_ovr_macro")
        print(f"{name:<12}{m['f1_macro']:>10.3f}{(roc or 0):>10.3f}"
              f"{fn['high_recall']:>13.3f}{ci_s:>22}")
    ab = report["ablation"]
    print(f"\nAblation (XGB) baseline f1={ab['baseline']['f1_macro']:.3f} -> "
          f"engineered f1={ab['engineered']['f1_macro']:.3f} (gain {ab['f1_gain']:+.3f})")
    op = report["optuna"]
    print(f"Optuna: baseline xgb f1={op['baseline_xgb_f1']:.3f} -> "
          f"optimized f1={op['optimized_xgb_f1']:.3f} (gain {op['f1_gain']:+.3f})")
    cal = report["calibration_comparison"]
    print(f"Calibration: raw brier(HIGH)={cal['raw_brier_high']} -> "
          f"sigmoid={cal['sigmoid_calibrated_brier_high']}")
    print(f"\nSelected: {report['selected_model']['kind']} "
          f"(score {report['selected_model']['selection_score']:.3f}) "
          f"-> version {report['model_version']['version']}")
    print(f"Predictions stored: {report['predictions_stored']}")
    print("Report saved to models/training_report.json")
    print("=================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
