"""Example integration test - test API endpoints with TestClient.

Integration tests should:
- Test FastAPI endpoints using TestClient
- Test database queries (with test database)
- Test external service integrations (with mocks)
- Be reasonably fast (< 100ms each)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_root_endpoint_returns_json() -> None:
    """Test root endpoint returns valid JSON response."""
    response = client.get("/")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "environment" in data
