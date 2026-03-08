"""Application-level domain exceptions."""

from __future__ import annotations


class AppException(Exception):
    """Base exception for application domain errors."""

    def __init__(
        self,
        *,
        status_code: int,
        type: str = "about:blank",
        title: str,
        detail: str,
    ) -> None:
        """Initialize the exception with HTTP response details."""
        self.status_code = status_code
        self.type = type
        self.title = title
        self.detail = detail
        super().__init__(detail)


class ConflictException(AppException):
    """Raised when a resource already exists (409)."""

    def __init__(self, *, detail: str) -> None:
        """Initialize a conflict exception with a detail message."""
        super().__init__(
            status_code=409,
            type="conflict",
            title="Resource Conflict",
            detail=detail,
        )
