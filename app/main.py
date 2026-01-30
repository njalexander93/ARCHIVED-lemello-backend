"""FastAPI application entry point.

Main application factory with CORS middleware and router registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health

# Create FastAPI application instance
app = FastAPI(
    title="Lemello Backend API",
    description="AI-powered cooking assistant and recipe creation platform",
    version="0.1.0",
    debug=settings.app_debug,
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
