"""Test health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """Create a fresh TestClient for each test."""
    return TestClient(app)


@pytest.mark.integration
def test_health_check(test_client: TestClient) -> None:
    """Test the health check endpoint returns 200."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
def test_root_endpoint(test_client: TestClient) -> None:
    """Test the root endpoint returns API info."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Lemello Backend API"
    assert data["version"] == "0.1.0"
