# Lemello Backend - Development Commands
# Usage: make <target>

.PHONY: help install test lint format type-check pre-commit clean

help:  ## Show this help message
	@echo "Lemello Backend - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with Poetry
	poetry install

test:  ## Run all tests with coverage
	poetry run pytest -v

test-unit:  ## Run only unit tests (fast)
	poetry run pytest tests/unit/ -v

test-integration:  ## Run only integration tests
	poetry run pytest tests/integration/ -v

test-watch:  ## Run tests in watch mode (re-run on changes)
	poetry run pytest-watch

lint:  ## Run ruff linter
	poetry run ruff check app/ tests/

format:  ## Format code with ruff
	poetry run ruff format app/ tests/

format-check:  ## Check if code is formatted (CI)
	poetry run ruff format --check app/ tests/

type-check:  ## Run mypy type checker
	poetry run mypy app/

pre-commit:  ## Run all pre-commit hooks manually
	poetry run pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks to latest versions
	poetry run pre-commit autoupdate

clean:  ## Remove cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage

dev:  ## Run development server with hot reload
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:  ## Start Docker containers
	cd .. && docker compose up -d

docker-down:  ## Stop Docker containers
	cd .. && docker compose down

docker-logs:  ## Show Docker container logs
	cd .. && docker compose logs -f backend

ci:  ## Run all CI checks (lint, type-check, test)
	@echo "Running CI checks..."
	@make format-check
	@make lint
	@make type-check
	@make test
	@echo "✅ All CI checks passed!"
