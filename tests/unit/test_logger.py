"""Unit tests for structured logging functionality."""

import json
import logging

import pytest

from app.core.logger import (
    CorrelationIDFilter,
    JSONFormatter,
    TextFormatter,
    correlation_id_var,
    sanitizer,
)

pytestmark = pytest.mark.unit


class TestSanitizer:
    """Test sanitary-based sensitive data sanitization."""

    def test_sanitize_simple_password(self):
        """Test that password field is redacted."""
        data = {"username": "test", "password": "secret123"}
        result = sanitizer.sanitize(data)
        assert result["username"] == "test"
        assert result["password"] == "********"

    def test_sanitize_case_insensitive(self):
        """Test that sanitization is case-insensitive."""
        data = {"Password": "secret", "TOKEN": "abc123"}
        result = sanitizer.sanitize(data)
        assert result["Password"] == "********"
        assert result["TOKEN"] == "********"

    def test_sanitize_nested_dict(self):
        """Test that nested dictionaries are sanitized."""
        data = {
            "user": {"name": "test", "password": "secret"},
            "api_key": "key123",
        }
        result = sanitizer.sanitize(data)
        assert result["user"]["name"] == "test"
        assert result["user"]["password"] == "********"
        assert result["api_key"] == "********"

    def test_sanitize_list_of_dicts(self):
        """Test that lists containing dicts are sanitized."""
        data = {
            "users": [
                {"name": "user1", "token": "token1"},
                {"name": "user2", "secret": "secret2"},
            ]
        }
        result = sanitizer.sanitize(data)
        assert result["users"][0]["name"] == "user1"
        assert result["users"][0]["token"] == "********"
        assert result["users"][1]["name"] == "user2"
        assert result["users"][1]["secret"] == "********"

    def test_sanitize_preserves_safe_fields(self):
        """Test that non-sensitive fields are preserved."""
        data = {
            "username": "test",
            "email": "test@example.com",
            "role": "admin",
        }
        result = sanitizer.sanitize(data)
        assert result == data


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["level"] == "INFO"
        assert log_dict["logger"] == "test.logger"
        assert log_dict["message"] == "Test message"
        assert "timestamp" in log_dict
        assert "pid" in log_dict

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = "12345"
        record.action = "create"

        output = formatter.format(record)
        log_dict = json.loads(output)

        # sanitary may preserve types, so check string representation
        assert str(log_dict["user_id"]) == "12345"
        assert log_dict["action"] == "create"

    def test_format_with_correlation_id(self):
        """Test formatting with correlation ID."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "req_abc123"

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["correlation_id"] == "req_abc123"

    def test_format_sanitizes_sensitive_data(self):
        """Test that sensitive data in extra fields is sanitized."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.username = "test"
        record.password = "secret123"

        output = formatter.format(record)
        log_dict = json.loads(output)

        assert log_dict["username"] == "test"
        assert log_dict["password"] == "********"


class TestTextFormatter:
    """Test text log formatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "Test message" in output
        # Should contain ANSI color codes
        assert "\033[" in output

    def test_format_with_correlation_id(self):
        """Test formatting with correlation ID."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "req_abc123"

        output = formatter.format(record)

        assert "[req_abc123]" in output

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields (should be indented)."""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = "12345"
        record.action = "create"

        output = formatter.format(record)

        assert "user_id: 12345" in output
        assert "action: create" in output
        # Extra fields should be indented
        assert "\n  " in output

    def test_format_different_levels(self):
        """Test that different log levels have different colors."""
        formatter = TextFormatter()

        levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]

        outputs = []
        for level in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )
            outputs.append(formatter.format(record))

        # All outputs should contain color codes
        for output in outputs:
            assert "\033[" in output

        # Outputs should be different (different colors)
        assert len(set(outputs)) == len(levels)


class TestCorrelationIDFilter:
    """Test correlation ID filter."""

    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation ID from context."""
        token = correlation_id_var.set("test_correlation_id")
        filter_obj = CorrelationIDFilter()

        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )

            result = filter_obj.filter(record)

            assert result is True
            assert hasattr(record, "correlation_id")
            assert record.correlation_id == "test_correlation_id"
        finally:
            correlation_id_var.reset(token)

    def test_filter_without_correlation_id(self):
        """Test that filter handles missing correlation ID gracefully."""
        token = correlation_id_var.set("")
        filter_obj = CorrelationIDFilter()

        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )

            result = filter_obj.filter(record)

            assert result is True
            # Should not have correlation_id if context var is empty
            assert not hasattr(record, "correlation_id")
        finally:
            correlation_id_var.reset(token)
