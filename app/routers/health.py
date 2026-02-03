"""Health check endpoint for monitoring and hot reload testing."""

from typing import Any, Dict

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.logger import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check(response: Response) -> Dict[str, Any]:
    """Return application health status with dependency checks.

    This endpoint is used for:
    - Container health checks
    - Load balancer health probes
    - Hot reload verification during development

    Returns:
        Dictionary with status and checks for configured dependencies.
    """
    health_status: Dict[str, Any] = {
        "status": "ok",
        "message": "Lemello Backend is running",
        "checks": {},
    }

    # Check database if configured
    if settings.database_url:
        try:
            # TODO: Add actual database ping when database is set up
            # await database.execute("SELECT 1")
            health_status["checks"]["database"] = "not_implemented"
        except Exception:
            logger.exception("Database health check failed")
            health_status["checks"]["database"] = "error"
            health_status["status"] = "degraded"

    # Check Redis if configured
    if settings.redis_url:
        try:
            # TODO: Add actual Redis ping when Redis is set up
            # await redis.ping()
            health_status["checks"]["redis"] = "not_implemented"
        except Exception:
            logger.exception("Redis health check failed")
            health_status["checks"]["redis"] = "error"
            health_status["status"] = "degraded"

    # Set appropriate HTTP status code
    if health_status["status"] == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(
            "Health check degraded",
            extra={"checks": health_status["checks"]},
        )

    return health_status
