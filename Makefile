.PHONY: up down migrate test lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd apps/api && uv run alembic upgrade head

test:
	cd apps/api && uv run pytest

lint:
	cd apps/api && uv run ruff check .
