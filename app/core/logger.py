"""Structured logging configuration with JSON and text formatters.

Provides centralized logging configuration with support for both human-readable
text output (development) and machine-parsable JSON output (production).
Includes correlation ID tracking for request tracing and sensitive data
filtering.
"""

import json
import logging
import os
import queue
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from typing import Optional

from sanitary import Sanitizer

from app.core.config import settings

# Correlation ID context variable for async-safe request tracking
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Sanitizer instance for removing sensitive data from logs
sanitizer = Sanitizer(
    keys={
        "password",
        "token",
        "secret",
        "authorization",
        "api_key",
        "bearer",
        "access_token",
        "refresh_token",
        "jwt",
        "api-key",
        "x-api-key",
        "cookie",
        "session",
        "csrf",
        "private_key",
        "passphrase",
    }
)

# LogRecord attributes to exclude from extra field output
EXCLUDED_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "thread",
    "threadName",
    "correlation_id",
    "exc_info",
    "exc_text",
    "stack_info",
    "taskName",
}

_file_log_listener: Optional[QueueListener] = None
_managed_handlers: list[logging.Handler] = []
_file_handler: Optional[logging.Handler] = None


class NonBlockingQueueHandler(QueueHandler):
    """QueueHandler that drops records when the queue is full."""

    def enqueue(self, record: logging.LogRecord) -> None:
        """Attempt to enqueue without blocking; drop if full."""
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            # Best-effort logging: drop if the queue is saturated.
            # Avoid recursive logging in a handler; write to stderr instead.
            try:
                sys.stderr.write("Log queue full; dropping log record.\n")
            except Exception:
                # Best-effort cleanup: ignore stderr write errors
                pass


def shutdown_logging() -> None:
    """Stop background log listeners and close managed handlers."""
    global _file_log_listener, _managed_handlers, _file_handler

    if _file_log_listener is not None:
        try:
            _file_log_listener.stop()
        finally:
            _file_log_listener = None

    # Close file handler if present
    if _file_handler is not None:
        try:
            _file_handler.flush()
        except Exception:
            # Best-effort cleanup: ignore flush errors on shutdown
            pass
        try:
            _file_handler.close()
        except Exception:
            # Best-effort cleanup: ignore close errors on shutdown
            pass
        _file_handler = None

    # Remove handlers previously added by this module
    root_logger = logging.getLogger()
    for handler in _managed_handlers:
        try:
            handler.flush()
        except Exception:
            # Best-effort cleanup: ignore flush errors on shutdown
            pass
        try:
            handler.close()
        except Exception:
            # Best-effort cleanup: ignore close errors on shutdown
            pass
        root_logger.removeHandler(handler)
    _managed_handlers = []


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production use.

    Outputs structured JSON logs suitable for log aggregation systems.
    Each log entry is a single-line JSON object with standardized fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            Single-line JSON string.
        """
        log_dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pid": record.process,
            "thread": record.threadName,
        }

        # Add correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_dict["correlation_id"] = correlation_id

        # Add extra fields from log record
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in EXCLUDED_LOG_RECORD_ATTRS
        }

        if extra_fields:
            sanitized = sanitizer.sanitize(extra_fields)
            for key, value in sanitized.items():
                if key not in log_dict:
                    log_dict[key] = value

        # Add exception info if present
        if record.exc_info:
            log_dict["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_dict, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text log formatter for development.

    Outputs colored, formatted logs with indented extra fields for
    improved readability during local development.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[37m",  # White
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[31m\033[1m",  # Red + Bold
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize the formatter.

        Args:
            use_colors: Whether to include ANSI color codes in output.
                       Set to False for file output.
        """
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as colored text.

        Args:
            record: The log record to format.

        Returns:
            Formatted, colored log string.
        """
        # Build timestamp
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

        # Get color for level (only if colors enabled)
        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.RESET)
            reset = self.RESET
        else:
            color = ""
            reset = ""

        # Get correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        correlation_str = f"[{correlation_id}] " if correlation_id else ""

        # Build base log line
        log_line = (
            f"{timestamp} {color}[{record.levelname}]{reset} "
            f"{correlation_str}{record.getMessage()}"
        )

        # Add extra fields if present
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in EXCLUDED_LOG_RECORD_ATTRS
        }

        if extra_fields:
            sanitized = sanitizer.sanitize(extra_fields)
            for key, value in sanitized.items():
                if key not in {"timestamp", "level", "logger", "message"}:
                    log_line += f"\n  {key}: {value}"

        # Add exception info if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        return log_line


class CorrelationIDFilter(logging.Filter):
    """Logging filter that injects correlation ID into log records.

    Retrieves the correlation ID from the context variable and adds it
    to the log record for consistent request tracing.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record.

        Args:
            record: The log record to modify.

        Returns:
            True (always allow the record to be logged).
        """
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        return True


def configure_logging() -> None:
    """Configure application-wide logging based on settings.

    Sets up the root logger with appropriate formatter (JSON or TEXT)
    and log level based on configuration. For TEXT format, optionally
    creates a file handler that saves logs to the backend repo's logs/
    directory with timestamped filenames for easier debugging.

    Should be called once during application startup.
    """
    global _file_log_listener, _managed_handlers, _file_handler

    # Get root logger
    root_logger = logging.getLogger()

    # Clean up prior logging state owned by this module
    shutdown_logging()

    # Avoid duplicate logging from uvicorn handlers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.propagate = True
        for handler in uvicorn_logger.handlers[:]:
            uvicorn_logger.removeHandler(handler)

    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Set formatter based on configuration
    formatter: logging.Formatter
    if settings.log_format.upper() == "JSON":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter(use_colors=True)

    console_handler.setFormatter(formatter)

    # Add correlation ID filter
    console_handler.addFilter(CorrelationIDFilter())

    # Add handler to root logger
    root_logger.addHandler(console_handler)
    _managed_handlers.append(console_handler)

    # For TEXT format, optionally log to file for easier debugging
    if settings.log_format.upper() == "TEXT" and settings.log_file_enabled:
        try:
            # Create logs directory if it doesn't exist
            logs_dir = Path(__file__).resolve().parents[2] / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped log filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            log_filename = logs_dir / f"lemello_{timestamp}_{os.getpid()}.log"

            # Create file handler with plain text (no colors)
            file_handler = logging.FileHandler(log_filename, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(TextFormatter(use_colors=False))
            file_handler.addFilter(CorrelationIDFilter())
            _file_handler = file_handler

            # Use a bounded queue to avoid blocking the event loop on file I/O
            log_queue: queue.Queue[logging.LogRecord] = queue.Queue(
                maxsize=1000
            )
            queue_handler = NonBlockingQueueHandler(log_queue)
            queue_handler.setLevel(log_level)
            queue_handler.addFilter(CorrelationIDFilter())

            # Start listener thread to write logs to file
            _file_log_listener = QueueListener(
                log_queue,
                file_handler,
                respect_handler_level=True,
            )
            _file_log_listener.start()

            # Add queue handler to root logger
            root_logger.addHandler(queue_handler)
            _managed_handlers.append(queue_handler)

            # Log the file location for user reference
            root_logger.info("Logging to file: %s", log_filename)
        except Exception as exc:
            root_logger.warning(
                "File logging disabled: %s",
                exc,
            )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.
              If None, returns the root logger.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
