#!/usr/bin/env python3
"""Load the synthetic dataset into PostgreSQL.

Uses PostgreSQL COPY for fast bulk loading (hundreds of thousands of rows in
a few seconds). Idempotent: `--fresh` truncates the academic tables first.
If the CSVs are missing it generates them first.

Usage:
    python scripts/seed.py --fresh
    python scripts/seed.py --data data/synthetic --database-url postgresql+psycopg2://...
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys

import pandas as pd

# Make `app` importable when run from the repo root or backend/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.db.session import engine  # noqa: E402

# Load order respects foreign-key dependencies.
LOAD_ORDER = [
    "students",
    "courses",
    "topics",
    "enrollments",
    "assessments",
    "questions",
    "assessment_results",
    "question_results",
    "attendance",
    "student_topic_mastery",
    "feedback",
]


def ensure_data(data_dir: str, seed: int, students: int) -> None:
    if os.path.exists(os.path.join(data_dir, "students.csv")):
        return
    print(f"No data in {data_dir}; generating…")
    gen = os.path.join(os.path.dirname(__file__), "generate_data.py")
    subprocess.check_call(
        [sys.executable, gen, "--seed", str(seed), "--students", str(students),
         "--out", data_dir]
    )


def copy_table(raw_conn, table: str, df: pd.DataFrame) -> int:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    cols = ",".join(df.columns)
    with raw_conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')", buf
        )
    return len(df)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join("data", "synthetic"))
    ap.add_argument("--fresh", action="store_true", help="truncate academic tables first")
    ap.add_argument("--seed", type=int, default=settings.RANDOM_SEED)
    ap.add_argument("--students", type=int, default=1000)
    ap.add_argument("--database-url", default=None)
    args = ap.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    ensure_data(args.data, args.seed, args.students)
    init_db()  # ensure schema + pgvector exist

    raw = engine.raw_connection()
    try:
        if args.fresh:
            with raw.cursor() as cur:
                cur.execute(
                    "TRUNCATE "
                    + ", ".join(LOAD_ORDER)
                    + " RESTART IDENTITY CASCADE"
                )
            raw.commit()
            print("Truncated academic tables.")

        total = 0
        for table in LOAD_ORDER:
            path = os.path.join(args.data, f"{table}.csv")
            df = pd.read_csv(path)
            n = copy_table(raw, table, df)
            total += n
            print(f"  loaded {n:>7,} rows into {table}")
        # Reset the serial sequence for questions (loaded with explicit ids).
        with raw.cursor() as cur:
            cur.execute(
                "SELECT setval(pg_get_serial_sequence('questions','id'), "
                "COALESCE((SELECT MAX(id) FROM questions), 1))"
            )
        raw.commit()
        print(f"Done. {total:,} rows loaded.")
    finally:
        raw.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
