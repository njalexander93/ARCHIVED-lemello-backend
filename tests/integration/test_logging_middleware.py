"""Integration tests for logging middleware and correlation IDs."""

import logging

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


class TestCorrelationIDMiddleware:
    """Test correlation ID middleware functionality."""

    def test_generates_correlation_id_when_missing(
        self, test_client: TestClient
    ):
        """Test that middleware generates correlation ID if not provided."""
        import uuid

        response = test_client.get("/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        # Should be a valid UUID
        correlation_id = response.headers["X-Correlation-ID"]
        assert uuid.UUID(correlation_id)

    def test_uses_provided_correlation_id(self, test_client: TestClient):
        """Test that middleware uses correlation ID from request header."""
        test_correlation_id = "test-correlation-123"
        response = test_client.get(
            "/health",
            headers={"X-Correlation-ID": test_correlation_id},
        )

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    def test_correlation_id_in_logs(self, test_client: TestClient, caplog):
        """Test that correlation ID appears in log output."""
        test_correlation_id = "test-log-correlation-456"

        with caplog.at_level(logging.INFO):
            response = test_client.get(
                "/health",
                headers={"X-Correlation-ID": test_correlation_id},
            )

            assert response.status_code == 200

            # Check logs contain correlation ID in any of the log records
            found_correlation = False
            for record in caplog.records:
                if hasattr(record, "correlation_id"):
                    if record.correlation_id == test_correlation_id:
                        found_correlation = True
                        break

            assert found_correlation, "Correlation ID not found in log records"


class TestRequestLogging:
    """Test request/response logging."""

    def test_logs_request_start_and_completion(
        self, test_client: TestClient, caplog
    ):
        """Test that requests are logged with start and completion."""
        with caplog.at_level(logging.INFO):
            response = test_client.get("/health")

            assert response.status_code == 200

            # Check for request-related log messages
            log_messages = [record.getMessage() for record in caplog.records]
            assert any("Request started" in msg for msg in log_messages)
            assert any("Request completed" in msg for msg in log_messages)

    def test_logs_request_method_and_path(
        self, test_client: TestClient, caplog
    ):
        """Test that request method and path are logged."""
        with caplog.at_level(logging.INFO):
            response = test_client.get("/health")

            assert response.status_code == 200

            # Check log records for method and path
            found_request_info = False
            for record in caplog.records:
                if (
                    hasattr(record, "request_method")
                    and record.request_method == "GET"
                    and hasattr(record, "request_path")
                    and record.request_path == "/health"
                ):
                    found_request_info = True
                    break

            assert found_request_info

    def test_logs_duration(self, test_client: TestClient, caplog):
        """Test that request duration is logged."""
        with caplog.at_level(logging.INFO):
            response = test_client.get("/health")

            assert response.status_code == 200

            # Check for duration in log records
            found_duration = False
            for record in caplog.records:
                if hasattr(record, "duration_ms"):
                    found_duration = True
                    break

            assert found_duration

    def test_logs_error_responses_as_warning(
        self, test_client: TestClient, caplog
    ):
        """Test that 4xx/5xx responses are logged at warning level."""
        with caplog.at_level(logging.WARNING):
            # Try to access a non-existent endpoint
            response = test_client.get("/nonexistent")

            assert response.status_code == 404

            # Check for warning level logs or 404 status
            found_error_log = False
            for record in caplog.records:
                if record.levelno >= logging.WARNING:
                    if (
                        hasattr(record, "response_status")
                        and record.response_status == 404
                    ):
                        found_error_log = True
                        break

            assert found_error_log


class TestLifecycleLogging:
    """Test application lifecycle event logging."""

    def test_startup_logs_application_info(self, caplog):
        """Test that startup event logs application information."""
        from app import __version__
        from app.main import app

        # Startup events happen when TestClient is created
        with caplog.at_level(logging.INFO):
            with TestClient(app) as client:
                client.get("/health")

        # Check for startup-related logs
        log_messages = [record.getMessage() for record in caplog.records]
        log_text = " ".join(log_messages).lower()

        # Check if startup was logged or if version info is present
        startup_logged = (
            "starting" in log_text
            or "startup" in log_text
            or any(__version__ in msg for msg in log_messages)
        )

        assert startup_logged

    def test_shutdown_logs_message(self, caplog):
        """Test that shutdown event logs a message."""
        from app.main import app

        with caplog.at_level(logging.INFO):
            with TestClient(app):
                pass

        log_messages = [record.getMessage() for record in caplog.records]
        assert any(
            "shutting down" in message.lower() for message in log_messages
        )
