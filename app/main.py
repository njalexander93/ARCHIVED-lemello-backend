"""FastAPI application entry point.

Main application factory with CORS middleware and router registration.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Environment, settings
from app.routers import health

# Create FastAPI application instance
app = FastAPI(
    title="Lemello Backend API",
    description="AI-powered cooking assistant and recipe creation platform",
    version="0.1.0",
    debug=settings.app_debug,
)

# Configure trusted hosts (prevents host header injection)
# In development, allow testserver for TestClient
if settings.app_env == Environment.PRODUCTION:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*.lemello.com",
            "lemello.com",
        ],
    )
else:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "testserver",  # For TestClient
            "*.lemello.com",
            "lemello.com",
        ],
    )

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


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
        "version": "0.1.0",
        "environment": settings.app_env,
    }
