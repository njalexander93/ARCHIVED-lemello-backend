<h1><img src=".github/assets/lemello-horizontal-yellow.svg" alt="Lemello" height="28px"> Backend</h1>

[![GitHub release](https://img.shields.io/github/v/release/lemello-app/backend)](https://github.com/lemello-app/backend/releases)
[![CI/CD](https://github.com/lemello-app/backend/actions/workflows/release.yml/badge.svg)](https://github.com/lemello-app/backend/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/python-3.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red)](#license)

The core service layer for Lemello — an AI-powered cooking platform that transforms nervous recipe-followers into confident recipe-creators.

---

## Overview

The backend is responsible for:

- Orchestrating AI-assisted recipe creation sessions (the "Sous-Chef" experience)
- Managing persistence of recipes, drafts, and forks
- Providing a secure API for the webapp
- Integrating with OpenAI models via an internal LLM gateway

Built with **FastAPI** following modern Python, security, and DevSecOps best practices.

---

## Related Repositories

| Repository | Description |
|------------|-------------|
| [lemello-app/webapp](https://github.com/lemello-app/webapp) | Next.js Progressive Web App |
| [lemello-app/infra](https://github.com/lemello-app/infra) | Terraform, Docker, and deployment configs |

---

## Requirements

- **Python 3.14.x** (Free-Threaded build recommended for production)
- **uv 0.9.28+** (for fast dependency management)
- PostgreSQL 16 (with pgvector)
- Redis (optional for local development)
- Docker (for containerized deployment)
- git

---

## Technology Stack

| Component      | Version | Classification | Rationale                                                                              |
| -------------- | ------- | -------------- | -------------------------------------------------------------------------------------- |
| **Python**     | 3.14.x  | Bleeding Edge  | Free-Threading (No GIL) enables parallel processing of Chat I/O and JSON Serialization |
| **FastAPI**    | Latest  | Stable         | High-performance async web framework                                                   |
| **Pydantic**   | v2.x    | Stable         | Strict validation with v2 compliance required                                          |
| **PostgreSQL** | 16      | Stable         | Managed database with pgvector support on DigitalOcean                                 |

---

## Code Style

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

## Deployment Target

Lemello Backend is deployed on **DigitalOcean App Platform** using containerized deployments.

### Infrastructure Overview

- **Compute:** DigitalOcean App Platform (Pro tier for Production, Basic for Staging)
- **Database:** DigitalOcean Managed PostgreSQL 16 with pgvector extension
- **Container Registry:** DigitalOcean Container Registry (DOCR)
- **Secrets:** Environment variables via App Platform (Production secrets managed securely)

### Build Once, Deploy Twice

The backend follows an immutable deployment strategy:

1. Docker images are built once and pushed to DOCR
2. The same image digest is deployed to both Staging and Production
3. Environment-specific configuration is injected via environment variables

---

## Installing Python 3.14

Lemello Backend is standardized on **Python 3.14**. All contributors and environments must use this version to ensure consistent behavior across development, CI, and production.

### Why Python 3.14?

Python 3.14 introduces **Free-Threading (No GIL)**, which enables true parallel processing. For Lemello's Creation Studio, this means:

- Parallel handling of WebSocket chat I/O and JSON serialization
- Elimination of UI jitter during the "Finalizing" phase
- Improved throughput for CPU-bound operations like Pydantic validation

### Debian / Ubuntu (Recommended: pyenv)

Using `pyenv` is the preferred method on Linux systems. It avoids conflicts with the system Python and allows explicit version control.

#### Install system dependencies

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  libffi-dev \
  liblzma-dev \
  uuid-dev \
  wget \
  curl \
  ca-certificates
```

#### Install pyenv

```bash
curl https://pyenv.run | bash
```

Add the following to your shell configuration (`~/.bashrc` or `~/.zshrc`):

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

Reload the shell:

```bash
exec "$SHELL"
```

#### Install Python 3.14

```bash
pyenv install 3.14.0
pyenv global 3.14.0
```

Verify:

```bash
python --version
# Python 3.14.x
```

#### Optional: Install Free-Threaded Build

For production deployments requiring true parallelism:

```bash
pyenv install 3.14.0t  # Free-threaded variant
```

---

### Debian / Ubuntu (Alternative: build from source)

Use this method only if `pyenv` is not permitted.

```bash
wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
tar -xvf Python-3.14.0.tgz
cd Python-3.14.0

./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall
```

Verify:

```bash
python3.14 --version
```

⚠️ Do not replace the system `python3` binary.

---

### Windows

#### Download Python 3.14

Download the **Python 3.14.x Windows x64 installer** from:

[https://www.python.org/downloads/](https://www.python.org/downloads/)

#### Install

During installation:

- Check **"Add Python to PATH"**
- Choose **"Customize installation"**
- Ensure **pip** is enabled
- Install for **all users** (recommended)

#### Verify

Open PowerShell:

```powershell
python --version
```

Expected output:

```text
Python 3.14.x
```

---

## Installing uv

uv is a fast Rust-based package manager used for dependency and virtual environment management.

Install uv after Python 3.14 is available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
# Expected: uv 0.9.28 or later
```

### Why uv?

- **10-100x faster** than pip/Poetry
- **Full Python 3.14 support** with no compatibility issues
- **Drop-in replacement** for pip with better dependency resolution
- **Production-ready** lock files that work correctly with Python 3.14

---

## Local Development Setup

### Clone the repository

```bash
git clone git@github.com:lemello-app/backend.git
cd backend
```

### Install dependencies

```bash
uv sync --all-extras
```

### Environment configuration

See the Environment Setup section below for `.env` configuration.

## Environment Setup

1. Copy the environment template:

```bash
cp .env.template .env
```

2. Configure required values:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `SECRET_KEY` | JWT signing key | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | OpenAI API key for model access | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| `DATABASE_URL` | Postgres connection string | Match infra `POSTGRES_*` values |
| `REDIS_URL` | Redis connection string | Match infra `REDIS_*` values |

3. Environment variables with double underscores (`__`) in Pydantic map to flat fields:

- Example: `AI__MODEL` env var maps to `settings.ai_model` field

4. See `.env.template` for the full list of defaults and options.

### Run the development server

```bash
uv run uvicorn app.main:app --reload
```

Or use the Makefile:

```bash
make dev
```

---

## Containerization

The backend uses a multi-stage Docker build to produce lean, immutable images suitable for the "Build Once, Deploy Twice" deployment strategy.

### Dockerfile Architecture

```dockerfile
# Stage 1: Builder
FROM python:3.14-slim AS builder
# Install build dependencies, create venv, install requirements

# Stage 2: Runtime
FROM python:3.14-slim AS runtime
# Copy only the virtual environment from builder
# Discard build artifacts for a lean production image
```

### Building the Container

```bash
docker build -t lemello-backend:latest .
```

### Running Locally with Docker

```bash
docker run -p 8000:8000 --env-file .env lemello-backend:latest
```

---

## App Platform Considerations

When deploying to DigitalOcean App Platform, keep these constraints in mind:

### Ephemeral Filesystem

App Platform containers have ephemeral file systems. Any data written to disk is lost upon deployment or restart. The FastAPI application must be **stateless**.

### Logging

Logs must be streamed to `stdout`/`stderr` for App Platform's logging agent. Configure Uvicorn to use a JSON logging formatter for structured logging:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record),
        })
```

### Shared Memory

AI libraries may use `/dev/shm` for shared memory. If you encounter `Bus error`, configure data loaders with `num_workers=0` or limit batch sizes to fit within RAM allocation.

---

## Dependency Management

- Dependencies are defined in `pyproject.toml`
- Exact versions are locked in `uv.lock`
- `uv.lock` **must be committed**
- Virtual environments **must not** be committed
- All dependencies must be **Pydantic v2 compliant**
- `.python-version` file pins Python 3.14 for the project

---

## Database Configuration

### PostgreSQL 16 with pgvector

Lemello uses DigitalOcean Managed PostgreSQL 16 with the `pgvector` extension for vector similarity search.

**Verified Configuration:**
- **PostgreSQL Version:** 16
- **pgvector Version:** 0.8.1 (verified 2026-02-01)
- **Tested with:** 1 GB RAM (DigitalOcean Basic Plan)
- **MVP Capacity:** 1,000-1,500 recipes + theory cards (~18 MB)

**Verification Commands:**
```sql
-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Create test table with 1536-dimensional vectors
CREATE TABLE recipes_test (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    embedding VECTOR(1536)
);

-- Insert sample data
INSERT INTO recipes_test (name, embedding)
VALUES ('Test Recipe', array_fill(0.1, ARRAY[1536])::vector);

-- Test vector similarity search
SELECT id, name,
       embedding <=> array_fill(0.15, ARRAY[1536])::vector AS distance
FROM recipes_test
ORDER BY distance
LIMIT 5;
```

**Scaling Considerations:**

For large-scale deployments (500K+ recipes), consider:
- **Binary Quantization:** Reduces memory footprint by 32x
- **pgvectorscale:** DiskANN-inspired indexing for disk-resident indexes
- **Scalar Quantization:** Half-precision fallback if Binary Quantization yields poor recall

### Connection String

The database URL is provided via environment variable:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require
```

---

## Releasing

### Version Management

This project uses semantic versioning (`MAJOR.MINOR.PATCH`):
- **PATCH** (0.1.0 → 0.1.1): Bug fixes, documentation updates
- **MINOR** (0.1.0 → 0.2.0): New features (backward compatible)
- **MAJOR** (0.1.0 → 1.0.0): Breaking changes

### Bumping the Version

**Manual version bump** (edit `pyproject.toml`):

```bash
# Edit backend/pyproject.toml line 3
version = "0.1.1"  # Change to your new version

# Commit the version bump
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
```

### Release Workflow

The CI/CD pipeline automatically handles releases:

1. **PR Stage**: Version uniqueness is checked
   - If version already exists, PR check fails with instructions
   - Ensures no duplicate releases

2. **Post-Merge**: Automatic release on merge to `main`
   - Runs full test suite (unit + integration + e2e)
   - Builds production Docker image
   - Pushes to GitHub Container Registry
   - Creates GitHub Release with tag `v{version}`

### Deployment

Pull the released Docker image:

```bash
# Specific version
docker pull ghcr.io/lemello-app/backend:0.1.0

# Latest
docker pull ghcr.io/lemello-app/backend:latest
```

---

## Security Notes

- Secrets are provided via environment variables
- `.env` files are never committed
- Production secrets are managed via DigitalOcean App Platform environment variables
- All user input is validated and sanitized via Pydantic models
- Use `trufflehog` for secret scanning in CI/CD

---

## License

**Copyright © Lemello, LLC. All rights reserved.**

The code contained herein is CONFIDENTIAL to Lemello, LLC. Portions
may also be trade secret. Any use, duplication, derivation, distribution or
disclosure of this code, for any reason, not expressly authorized in writing
by Lemello, LLC is prohibited. All rights are expressly reserved by Lemello, LLC.
