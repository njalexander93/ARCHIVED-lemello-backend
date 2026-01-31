"""Shared pytest fixtures for all tests.

This module contains fixtures that are available across all test suites
(unit, integration, and e2e tests).
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    """Create a fresh TestClient for each test.

    Yields:
        TestClient configured with the FastAPI app.
    """
    with TestClient(app) as client:
        yield client
