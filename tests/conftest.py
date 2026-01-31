"""Shared pytest fixtures for all tests.

This module contains fixtures that are available across all test suites
(unit, integration, and e2e tests).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> TestClient:
    """Create a fresh TestClient for each test.

    Returns:
        TestClient configured with the FastAPI app.
    """
    return TestClient(app)
