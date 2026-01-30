"""Health check endpoint for monitoring and hot reload testing."""

from typing import Dict

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Return application health status.

    This endpoint is used for:
    - Container health checks
    - Load balancer health probes
    - Hot reload verification during development

    Returns:
        Dictionary with status key indicating application health.
    """
    return {"status": "ok", "message": "Lemello Backend is running"}
