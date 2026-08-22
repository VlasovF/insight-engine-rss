.PHONY: help install install-dev precommit test docker-up docker-down docker-build docker-logs clean

.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@echo "  install       Install Python dependencies with uv"
	@echo "  install-dev   Install Python dev dependencies"
	@echo "  install-front Install frontend dependencies"
	@echo "  precommit     Run pre-commit hooks"
	@echo "  test          Run pytest"
	@echo "  docker-up     Start all containers"
	@echo "  docker-down   Stop all containers"
	@echo "  docker-build  Rebuild containers"
	@echo "  docker-logs   Show logs from all containers"
	@echo "  clean         Remove cache, logs, and database"

install:
	cd backend && uv sync

install-dev:
	cd backend && uv sync --extra dev

install-front:
	cd frontend && npm install

precommit:
	pre-commit run --all-files

test:
	cd backend && pytest -v

docker-up:
	docker compose --env-file .env up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

clean:
	rm -rf app.db chroma_data logs/ __pycache__/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find frontend -type d -name node_modules -exec rm -rf {} +