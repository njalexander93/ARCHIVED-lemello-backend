"""FastAPI application entry point.

Main application factory with CORS middleware and router registration.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.core.config import Environment, settings
from app.core.logger import configure_logging, correlation_id_var, get_logger
from app.routers import health

# Configure logging before application startup
configure_logging()
logger = get_logger(__name__)

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
    allow_headers=["Content-Type", "Authorization"],
)


# Application lifecycle events
@app.on_event("startup")
async def startup_event() -> None:
    """Log application startup with configuration details."""
    logger.info(
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
    logger.info("Application shutting down")


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
    correlation_id = request.headers.get("X-Correlation-ID") or str(
        uuid.uuid4()
    )

    # Store in context for this request
    correlation_id_var.set(correlation_id)

    # Log request start
    logger.info(
        "Request started",
        extra={
            "request_method": request.method,
            "request_path": str(request.url.path),
            "request_query": (
                str(request.url.query) if request.url.query else None
            ),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    # Process request and measure duration
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    # Log request completion
    log_level = "warning" if response.status_code >= 400 else "info"
    getattr(logger, log_level)(
        "Request completed",
        extra={
            "request_method": request.method,
            "request_path": str(request.url.path),
            "response_status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )

    return response


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

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # XSS protection (legacy, but still useful for older browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # HSTS (only in production)
    if settings.app_env == Environment.PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


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
