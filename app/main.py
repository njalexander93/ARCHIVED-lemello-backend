"""FastAPI application entry point.

Main application factory with CORS middleware and router registration.
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.core.config import Environment, settings
from app.core.logger import (
    configure_logging,
    correlation_id_var,
    get_logger,
    shutdown_logging,
)
from app.routers import health

log = get_logger(__name__)

# Create FastAPI application instance
app = FastAPI(
    title="Lemello Backend API",
    description="AI-powered cooking assistant and recipe creation platform",
    version=__version__,
    debug=settings.app_debug,
)

# Configure trusted hosts (prevents host header injection)
if settings.app_env == Environment.PRODUCTION:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*.lemello.com",
            "lemello.com",
        ],
    )
elif settings.app_env == Environment.STAGING:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*.lemello.com",
            "lemello.com",
        ],
    )
else:  # Development
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "0.0.0.0",  # Docker container bind
            "testserver",  # For TestClient
            "*.lemello.com",
            "lemello.com",
        ],
    )

# Configure CORS based on environment
if settings.app_env == Environment.PRODUCTION:
    cors_origins = [
        "https://lemello.com",
        "https://www.lemello.com",
        "https://app.lemello.com",
    ]
elif settings.app_env == Environment.STAGING:
    cors_origins = [
        "https://staging.lemello.com",
        "http://localhost:3000",  # Allow local dev against staging API
        "http://127.0.0.1:3000",
    ]
else:  # Development
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)


# Application lifecycle events
@app.on_event("startup")
async def startup_event() -> None:
    """Log application startup with configuration details."""
    configure_logging()
    log.info(
        "Application starting",
        extra={
            "version": __version__,
            "environment": settings.app_env.value,
            "log_level": settings.log_level,
            "log_format": settings.log_format,
            "debug_mode": settings.app_debug,
        },
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Log application shutdown."""
    log.info("Application shutting down")
    shutdown_logging()


def apply_security_headers(response: Response) -> Response:
    """Add security headers to a response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.app_env == Environment.PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(HTTPException)
async def http_exception_with_correlation(
    request: Request, exc: HTTPException
) -> Response:
    """Attach correlation ID to HTTP error responses."""
    response = await http_exception_handler(request, exc)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    return apply_security_headers(response)


@app.exception_handler(RequestValidationError)
async def validation_exception_with_correlation(
    request: Request, exc: RequestValidationError
) -> Response:
    """Attach correlation ID to validation error responses."""
    response = await request_validation_exception_handler(request, exc)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    return apply_security_headers(response)


# Correlation ID and request logging middleware
@app.middleware("http")
async def correlation_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add correlation ID to request context and log request/response.

    Extracts or generates a correlation ID for request tracing, stores it in
    context, and logs request start/completion with timing information.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or route handler.

    Returns:
        Response with X-Correlation-ID header added.
    """
    # Extract or generate correlation ID
    correlation_id = str(uuid.uuid4())
    raw_correlation_id = request.headers.get("X-Correlation-ID")
    if raw_correlation_id:
        candidate = raw_correlation_id.strip()
        if len(candidate) <= 64 and re.fullmatch(r"[A-Za-z0-9._-]+", candidate):
            correlation_id = candidate

    # Store in context for this request
    token = correlation_id_var.set(correlation_id)
    request.state.correlation_id = correlation_id

    start_time = time.perf_counter()
    try:
        # Log request start
        log.info(
            "Request started",
            extra={
                "request_method": request.method,
                "request_path": str(request.url.path),
                "request_query_keys": (
                    list(request.query_params.keys())
                    if request.query_params
                    else None
                ),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Process request and measure duration
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log request completion
        log_level = "warning" if response.status_code >= 400 else "info"
        getattr(log, log_level)(
            "Request completed",
            extra={
                "request_method": request.method,
                "request_path": str(request.url.path),
                "response_status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
    finally:
        correlation_id_var.reset(token)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add security headers to all responses.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or route handler.

    Returns:
        Response with added security headers.
    """
    response = await call_next(request)
    return apply_security_headers(response)


# Register routers
app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API information.

    Returns:
        Dictionary with API name and version.
    """
    return {
        "name": "Lemello Backend API",
        "version": __version__,
        "environment": settings.app_env.value,
    }
