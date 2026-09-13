#!/usr/bin/env python3
"""Analyse and store feedback NLP fields, and optionally compare methods.

Usage:
    python scripts/analyze_feedback.py --method rule
    python scripts/analyze_feedback.py --method transformer --compare --sample 200
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.nlp.pipeline import analyze_and_store, compare_methods  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="rule", choices=["rule", "transformer", "llm"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--sample", type=int, default=200)
    args = ap.parse_args()

    configure_logging()
    with SessionLocal() as db:
        n = analyze_and_store(db, method=args.method, limit=args.limit)
        print(f"Stored NLP analysis for {n} feedback rows (method={args.method}).")
        if args.compare:
            print("\nMethod comparison (accuracy vs student rating):")
            print(json.dumps(compare_methods(db, sample=args.sample), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
