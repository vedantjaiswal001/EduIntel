#!/usr/bin/env python3
"""(Re)generate SHAP explanations for all stored predictions.

Normally run automatically at the end of scripts/train.py; provided separately
so explanations can be refreshed without retraining.

Usage: python scripts/explain.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.ml.explain import generate_explanations  # noqa: E402


def main() -> int:
    configure_logging()
    with SessionLocal() as db:
        n = generate_explanations(db, engine)
    print(f"Generated explanations for {n} predictions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
