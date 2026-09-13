#!/usr/bin/env python3
"""Seed synthetic demo interventions + outcomes for the Intervention Center.

Picks at-risk students, creates a system-recommended intervention for each, and
records a before/after outcome drawn from an honest distribution (mostly but not
always positive). Clearly synthetic demo data — the effectiveness view carries a
non-causal caveat.

Usage: python scripts/seed_interventions.py [--fresh] [--n 30]
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.logging import configure_logging  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.ml import serving  # noqa: E402
from app.models.intervention import Intervention, InterventionOutcome  # noqa: E402
from app.services import interventions as svc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    configure_logging()
    rng = random.Random(args.seed)

    with SessionLocal() as db:
        if args.fresh:
            db.query(InterventionOutcome).delete()
            db.query(Intervention).delete()
            db.commit()

        # target the highest-risk students, plus some medium
        targets = serving.get_at_risk_students(db, limit=args.n, label="HIGH_RISK")
        targets += serving.get_at_risk_students(db, limit=args.n // 3, label="MEDIUM_RISK")
        created = 0
        for pred in targets:
            rec = svc.recommend_for_student(db, pred.student_id)
            if not rec.get("recommendations"):
                continue
            top = rec["recommendations"][0]
            iv = svc.create_intervention(
                db, student_id=pred.student_id, type=top["type"], reason=top["reason"],
                expected_outcome="Improve assessment performance by the next checkpoint.",
                scheduled_date=date(2026, 3, 1), recommended_by="system")
            # honest outcome: mean improvement ~ +7, sd 11 (some negative)
            before = round(rng.uniform(28, 52), 1)
            delta = rng.gauss(7, 11)
            after = round(min(100.0, max(0.0, before + delta)), 1)
            svc.record_outcome(db, intervention_id=iv.id, metric="avg_score",
                               before_value=before, after_value=after,
                               notes="synthetic demo outcome")
            created += 1
        print(f"Seeded {created} interventions with outcomes.")
        eff = svc.effectiveness(db)
        print(f"Effectiveness: n={eff['n']} mean_delta={eff['mean_delta']} "
              f"improved_share={eff.get('improved_share')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
