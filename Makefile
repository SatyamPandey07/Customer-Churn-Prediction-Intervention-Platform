.PHONY: up down migrate test lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd apps/api && source .venv/bin/activate && alembic upgrade head

test:
	cd apps/api && source .venv/bin/activate && pytest

lint:
	cd apps/api && source .venv/bin/activate && ruff check .
