"""Standardized error response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FieldError(BaseModel):
    """Individual field-level validation error."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Unified error envelope for all API errors.

    Inspired by RFC 9457 (Problem Details for HTTP APIs).
    """

    type: str = Field(
        default="about:blank",
        description="Error type identifier",
    )
    title: str = Field(..., description="Short human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation")
    errors: list[FieldError] | None = Field(
        default=None,
        description="Field-level errors for validation failures",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "validation_error",
                    "title": "Validation Error",
                    "status": 400,
                    "detail": "Request body contains invalid fields.",
                    "errors": [
                        {
                            "field": "password",
                            "message": (
                                "String should have at least 8 characters"
                            ),
                        }
                    ],
                }
            ]
        }
    )
