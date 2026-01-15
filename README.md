# ChefAI Backend

The **ChefAI Backend** is the core service layer for ChefAI. It is responsible for:

- Orchestrating AI-assisted recipe creation sessions
- Managing persistence of recipes, drafts, and forks
- Providing a secure API for the frontend
- Integrating with OpenAI models via an internal LLM gateway

The backend is built with **FastAPI** and follows modern Python, security, and DevSecOps best practices.

---

## Requirements

- **Python 3.14.x**
- Poetry
- PostgreSQL 16 (with pgvector)
- Redis (optional for local development)
- git

---

## Installing Python 3.14

ChefAI Backend is standardized on **Python 3.14**. All contributors and environments must use this
version to ensure consistent behavior across development, CI, and production.

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
````

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

* Check **“Add Python to PATH”**
* Choose **“Customize installation”**
* Ensure **pip** is enabled
* Install for **all users** (recommended)

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

## Project Structure

```text
TBD
```

---

## Dependency Management

* Dependencies are defined in `pyproject.toml`
* Exact versions are locked in `poetry.lock`
* `poetry.lock` **must be committed**
* Virtual environments **must not** be committed

---

## Security Notes

* Secrets are provided via environment variables
* `.env` files are never committed
* Production secrets are managed via AWS Secrets Manager
* All user input is validated and sanitized

---

## License

Do NOT modify or remove this copyright and confidentiality notice.

**Copyright © Nikolai Alexander. All rights reserved.**

The code contained herein is CONFIDENTIAL to Nikolai Alexander. Portions
may also be trade secret. Any use, duplication, derivation, distribution or
disclosure of this code, for any reason, not expressly authorized in writing
by Nikolai Alexander is prohibited. All rights are expressly reserved by Nikolai Alexander.

---
