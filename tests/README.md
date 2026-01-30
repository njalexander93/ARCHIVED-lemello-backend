# Lemello Backend Tests

## Directory Structure

```
tests/
├── unit/              # Fast, isolated tests of pure functions
│   ├── __init__.py
│   └── test_*.py      # Test business logic, utilities, models
├── integration/       # Tests with external dependencies
│   ├── __init__.py
│   └── test_*.py      # Test API endpoints, database queries
└── e2e/              # End-to-end user workflow tests
    ├── __init__.py
    └── test_*.py      # Test complete user journeys (future)
```

## Test Types

| Type | Speed | Dependencies | When to Run | Example |
|------|-------|--------------|-------------|---------|
| **Unit** | ⚡ <10ms | None (mocked) | Every commit | Test recipe validation logic |
| **Integration** | 🏃 <100ms | TestClient, maybe DB | Pre-push | Test `/recipes` endpoint |
| **E2E** | 🐌 Seconds | Browser, full stack | CI/CD only | Test user creates recipe flow |

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test types
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/

# Run by marker
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m "not slow"

# Run with verbose output
poetry run pytest -v

# Run with coverage report
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/integration/test_health.py

# Run specific test function
poetry run pytest tests/integration/test_health.py::test_health_check
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_validators.py
import pytest

@pytest.mark.unit
def test_validate_email():
    """Test email validation logic."""
    assert validate_email("user@example.com") is True
    assert validate_email("invalid") is False
```

### Integration Test Example

```python
# tests/integration/test_recipes.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_create_recipe():
    """Test recipe creation endpoint."""
    response = client.post("/recipes", json={
        "title": "Test Recipe",
        "ingredients": ["salt", "pepper"]
    })
    assert response.status_code == 201
```

### E2E Test Example (Future)

```python
# tests/e2e/test_user_flow.py
import pytest

@pytest.mark.e2e
@pytest.mark.slow
def test_complete_recipe_creation_flow():
    """Test user creates and publishes recipe."""
    # Use Playwright/Selenium to automate browser
    # Test full user journey
```

## Test Markers

Tests can be marked with decorators for selective running:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests taking >1 second

## CI/CD Strategy

**Pre-commit hook:**
```bash
poetry run pytest tests/unit/ -x
```

**Pre-push hook:**
```bash
poetry run pytest tests/unit/ tests/integration/
```

**CI Pipeline:**
```bash
poetry run pytest  # All tests including e2e
```

## Coverage Goals

- **Overall:** >80%
- **Critical paths:** 100% (auth, payments, data validation)
- **Unit tests:** Should be majority of test suite
- **Integration tests:** Cover all API endpoints
- **E2E tests:** Cover critical user journeys only

## Best Practices

1. ✅ **Test behavior, not implementation**
2. ✅ **One assertion per test** (when possible)
3. ✅ **Use descriptive test names** (`test_user_cannot_delete_other_users_recipe`)
4. ✅ **Follow AAA pattern:** Arrange, Act, Assert
5. ✅ **Mock external services** in unit tests
6. ✅ **Keep tests independent** (no shared state)
7. ✅ **Test edge cases** (empty lists, None values, errors)

## Fixtures (Coming Soon)

When you add database tests, create shared fixtures:

```python
# tests/conftest.py
import pytest

@pytest.fixture
def test_db():
    """Provide clean test database."""
    # Setup test database
    yield db
    # Cleanup
```
