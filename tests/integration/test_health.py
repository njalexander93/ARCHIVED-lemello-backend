"""Test health check endpoint."""

import pytest
from fastapi.testclient import TestClient


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
    # Verify version field exists and has valid semver format (X.Y.Z)
    assert "version" in data
    assert isinstance(data["version"], str)
    version_parts = data["version"].split(".")
    assert len(version_parts) == 3
    assert all(part.isdigit() for part in version_parts)
