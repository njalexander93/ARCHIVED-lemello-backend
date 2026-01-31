# Lemello Backend - Development Commands
# Usage: make <target>

.PHONY: help install test lint format type-check pre-commit clean

help:  ## Show this help message
	@echo "Lemello Backend - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with uv
	uv sync --all-extras

test:  ## Run all tests with coverage
	uv run pytest -v

test-unit:  ## Run only unit tests (fast)
	uv run pytest tests/unit/ -v

test-integration:  ## Run only integration tests
	uv run pytest tests/integration/ -v

test-watch:  ## Run tests in watch mode (re-run on changes)
	uv run ptw --runner "uv run pytest"

lint:  ## Run ruff linter
	uv run ruff check app/ tests/

format:  ## Format code with ruff
	uv run ruff format app/ tests/

format-check:  ## Check if code is formatted (CI)
	uv run ruff format --check app/ tests/

type-check:  ## Run mypy type checker
	uv run mypy app/

pre-commit:  ## Run all pre-commit hooks manually
	uv run pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks to latest versions
	uv run pre-commit autoupdate

clean:  ## Remove cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage

dev:  ## Run development server with hot reload
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:  ## Start Docker containers
	docker compose up -d

docker-down:  ## Stop Docker containers
	docker compose down

docker-logs:  ## Show Docker container logs
	docker compose logs -f backend

ci:  ## Run all CI checks (lint, type-check, test)
	@echo "Running CI checks..."
	@make format-check
	@make lint
	@make type-check
	@make test
	@echo "✅ All CI checks passed!"
