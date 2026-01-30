# syntax=docker/dockerfile:1
# Lemello Backend - Multi-stage Docker build for FastAPI with hot reload

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.14-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=2.1.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev dependencies for production)
RUN poetry install --no-root --only main

# -----------------------------------------------------------------------------
# Stage 2: Development - Hot reload configuration
# -----------------------------------------------------------------------------
FROM python:3.14-slim AS development

WORKDIR /app

# Copy Poetry and virtual environment from builder
COPY --from=builder /opt/poetry /opt/poetry
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/opt/poetry/bin:/app/.venv/bin:$PATH"

# Copy project files
COPY pyproject.toml poetry.lock* ./
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run with uvicorn in reload mode for hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "/app/app"]

# -----------------------------------------------------------------------------
# Stage 3: Production - Lean runtime image
# -----------------------------------------------------------------------------
FROM python:3.14-slim AS production

WORKDIR /app

# Copy only the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY app/ ./app/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run with uvicorn (no reload in production)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
