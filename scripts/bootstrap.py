#!/usr/bin/env python3
"""One-command setup: generate + load data, train the model, ingest documents,
analyse feedback, and seed demo interventions. Reproducible (fixed seeds).

Usage:
    python scripts/bootstrap.py            # full setup
    python scripts/bootstrap.py --fast     # fewer Optuna trials
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)


def run(args: list[str]) -> None:
    print(f"\n▶ {' '.join(args)}")
    subprocess.check_call([sys.executable, *args])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--students", type=int,
                    default=int(os.getenv("EDUINTEL_SEED_STUDENTS", "1000")),
                    help="number of synthetic students (env: EDUINTEL_SEED_STUDENTS)")
    args = ap.parse_args()
    trials = "8" if args.fast else "25"
    students = str(args.students)

    run([os.path.join(HERE, "seed.py"), "--fresh", "--students", students])
    run([os.path.join(HERE, "train.py"), "--seed", "42", "--trials", trials])
    run([os.path.join(HERE, "ingest_docs.py"), "--fresh"])
    run([os.path.join(HERE, "analyze_feedback.py"), "--method", "rule"])
    run([os.path.join(HERE, "seed_interventions.py"), "--fresh"])
    print("\n✅ Bootstrap complete. Start the API: uvicorn app.main:app --reload (from backend/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
