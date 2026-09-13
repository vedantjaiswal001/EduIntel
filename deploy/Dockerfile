# EduIntel — single-service production image.
# Builds the React frontend, then runs the FastAPI backend which serves BOTH the
# API and the built SPA. Uses the lightweight (no-torch) dependency set so it
# fits a small cloud instance. Build context = repo root.

# ---- stage 1: build the frontend ----
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build   # -> /fe/dist

# ---- stage 2: backend runtime ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_DIR=/app/models \
    DATA_DIR=/app/data \
    FRONTEND_DIST=/app/frontend_dist \
    PYTHONPATH=/app/backend
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-deploy.txt ./requirements-deploy.txt
RUN pip install --upgrade pip && pip install -r requirements-deploy.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY --from=frontend /fe/dist ./frontend_dist
COPY deploy/start.sh ./start.sh
RUN chmod +x ./start.sh && mkdir -p /app/models /app/data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/api/health || exit 1
CMD ["./start.sh"]
