# ChefAI Backend

The **ChefAI Backend** is the core service layer for ChefAI. It is responsible for:

- Orchestrating AI-assisted recipe creation sessions
- Managing persistence of recipes, drafts, and forks
- Providing a secure API for the frontend
- Integrating with OpenAI models via an internal LLM gateway

The backend is built with **FastAPI** and follows modern Python, security, and DevSecOps best practices.

---

## Requirements

- **Python 3.14.x** (Free-Threaded build recommended for production)
- Poetry
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

## Deployment Target

ChefAI Backend is deployed on **DigitalOcean App Platform** using containerized deployments.

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

ChefAI Backend is standardized on **Python 3.14**. All contributors and environments must use this
version to ensure consistent behavior across development, CI, and production.

### Why Python 3.14?

Python 3.14 introduces **Free-Threading (No GIL)**, which enables true parallel processing. For
ChefAI's "Creation Studio," this means:

- Parallel handling of WebSocket chat I/O and JSON serialization
- Elimination of UI jitter during the "Finalizing" phase
- Improved throughput for CPU-bound operations like Pydantic validation

### Debian / Ubuntu (Recommended: pyenv)

Using `pyenv` is the preferred method on Linux systems. It avoids conflicts with the system Python
and allows explicit version control.

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

## Installing Poetry

Poetry is used for dependency and virtual environment management.

Install Poetry after Python 3.14 is available:

```bash
curl -sSL https://install.python-poetry.org | python -
```

Verify:

```bash
poetry --version
```

---

## Local Development Setup

### Clone the repository

```bash
git clone <repo-url>
cd chefai-backend
```

### Install dependencies

```bash
poetry install
```

### Environment configuration

Copy the environment template and fill in values:

```bash
cp .env.template .env
```

### Run the development server

```bash
poetry run uvicorn app.main:app --reload
```

---

## Containerization

The backend uses a multi-stage Docker build to produce lean, immutable images suitable for the
"Build Once, Deploy Twice" deployment strategy.

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
docker build -t chefai-backend:latest .
```

### Running Locally with Docker

```bash
docker run -p 8000:8000 --env-file .env chefai-backend:latest
```

---

## App Platform Considerations

When deploying to DigitalOcean App Platform, keep these constraints in mind:

### Ephemeral Filesystem

App Platform containers have ephemeral file systems. Any data written to disk is lost upon
deployment or restart. The FastAPI application must be **stateless**.

### Logging

Logs must be streamed to `stdout`/`stderr` for App Platform's logging agent. Configure Uvicorn
to use a JSON logging formatter for structured logging:

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

AI libraries may use `/dev/shm` for shared memory. If you encounter `Bus error`, configure
data loaders with `num_workers=0` or limit batch sizes to fit within RAM allocation.

---

## Project Structure

```text
TBD
```

---

## Dependency Management

- Dependencies are defined in `pyproject.toml`
- Exact versions are locked in `poetry.lock`
- `poetry.lock` **must be committed**
- Virtual environments **must not** be committed
- All dependencies must be **Pydantic v2 compliant**

---

## Database Configuration

### PostgreSQL 16 with pgvector

ChefAI uses DigitalOcean Managed PostgreSQL 16 with the `pgvector` extension for vector similarity
search. For large-scale deployments (4M+ recipes), consider:

- **Binary Quantization:** Reduces memory footprint by 32x
- **pgvectorscale:** DiskANN-inspired indexing for disk-resident indexes
- **Scalar Quantization:** Half-precision fallback if Binary Quantization yields poor recall

### Connection String

The database URL is provided via environment variable:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require
```

---

## Security Notes

- Secrets are provided via environment variables
- `.env` files are never committed
- Production secrets are managed via DigitalOcean App Platform environment variables
- All user input is validated and sanitized via Pydantic models
- Use `trufflehog` for secret scanning in CI/CD

---

## Suggested Additions

Consider adding the following sections as the project matures:

- [ ] **API Documentation:** Link to auto-generated OpenAPI/Swagger docs
- [ ] **Testing:** Instructions for running unit and integration tests
- [ ] **CI/CD Pipeline:** GitHub Actions workflow documentation
- [ ] **Monitoring:** Logging and observability setup
- [ ] **WebSocket Configuration:** Details for the Creation Studio real-time features
- [ ] **LLM Gateway:** Configuration for the OpenAI adapter

---

## License

Do NOT modify or remove this copyright and confidentiality notice.

**Copyright © Nikolai Alexander. All rights reserved.**

The code contained herein is CONFIDENTIAL to Nikolai Alexander. Portions
may also be trade secret. Any use, duplication, derivation, distribution or
disclosure of this code, for any reason, not expressly authorized in writing
by Nikolai Alexander is prohibited. All rights are expressly reserved by Nikolai Alexander.

---
