#!/usr/bin/env sh
# Production entrypoint: ensure schema, seed demo data once, then serve.
set -e
cd /app/backend

echo "[start] ensuring database schema + pgvector…"
python -m app.db.init_db || true

COUNT=$(python - <<'PY'
from sqlalchemy import text
from app.db.session import engine
n = 0
try:
    with engine.connect() as c:
        n = c.execute(text("select count(*) from students")).scalar() or 0
except Exception:
    n = 0
print(n)
PY
)
echo "[start] students already in DB: $COUNT"

if [ "$COUNT" = "0" ]; then
  echo "[start] first boot — seeding demo data (${EDUINTEL_SEED_STUDENTS:-400} students)…"
  cd /app && python scripts/bootstrap.py --fast || echo "[start] seeding failed; starting server anyway"
  cd /app/backend
fi

echo "[start] launching web server on port ${PORT:-8000}…"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
