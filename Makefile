# EduIntel developer commands.
# Most targets assume a running PostgreSQL and DATABASE_URL set (or .env).

.PHONY: help install install-frontend seed train ingest feedback interventions \
        bootstrap test lint backend frontend up down build clean

help:
	@echo "EduIntel make targets:"
	@echo "  install         Install backend deps (backend/requirements-dev.txt)"
	@echo "  install-frontend Install frontend deps"
	@echo "  bootstrap       Full data setup: seed + train + ingest + feedback + interventions"
	@echo "  seed            Generate + load synthetic data"
	@echo "  train           Train the risk model (comparison, ablation, Optuna)"
	@echo "  ingest          Ingest synthetic course documents into the RAG KB"
	@echo "  test            Run the backend test suite"
	@echo "  backend         Run the API (uvicorn, reload)"
	@echo "  frontend        Run the React dev server"
	@echo "  up / down       docker compose up --build / down"

install:
	cd backend && pip install -r requirements-dev.txt

install-frontend:
	cd frontend && npm install

seed:
	cd backend && python ../scripts/seed.py --fresh

train:
	cd backend && python ../scripts/train.py --seed 42 --trials 25

ingest:
	cd backend && python ../scripts/ingest_docs.py --fresh

feedback:
	cd backend && python ../scripts/analyze_feedback.py --method rule

interventions:
	cd backend && python ../scripts/seed_interventions.py --fresh

bootstrap:
	cd backend && python ../scripts/bootstrap.py

test:
	cd backend && python -m pytest tests -q

lint:
	cd backend && ruff check app || true

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build

down:
	docker compose down

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
