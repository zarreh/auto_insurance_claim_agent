.PHONY: install run-api run-frontend run docker-build docker-up docker-down test lint format clean ingest docs-serve docs-build

# ─── Dependencies ───────────────────────────────────────────────────────────────

install:
	poetry install

# ─── Local Development ──────────────────────────────────────────────────────────

run-api:
	poetry run python -m claim_agent.main

run-frontend:
	cd frontend && poetry run streamlit run app.py --server.port=8504 --server.address=0.0.0.0

run:
	poetry run python -m claim_agent.main &
	sleep 2
	cd frontend && poetry run streamlit run app.py --server.port=8501 --server.address=0.0.0.0; \
	kill %1 2>/dev/null || true

# ─── Docker ─────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ─── Data Ingestion ─────────────────────────────────────────────────────────────

ingest:
	poetry run python -m claim_agent.core.ingestion

# ─── Testing & Quality ──────────────────────────────────────────────────────────

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check src/ tests/ frontend/
	poetry run mypy src/

format:
	poetry run ruff format src/ tests/ frontend/
	poetry run ruff check --fix src/ tests/ frontend/

# ─── Documentation ──────────────────────────────────────────────────────────────

docs-serve:
	poetry run mkdocs serve

docs-build:
	poetry run mkdocs build --strict

# ─── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/
