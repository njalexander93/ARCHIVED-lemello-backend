"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import AuthResponse, TokenResponse
from app.schemas.errors import ErrorResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Creates a new user account with email, username, and password. "
        "Returns a JWT access token and user profile on success. "
        "Email and username must be unique (case-insensitive)."
    ),
    responses={
        400: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
        409: {
            "description": "Email or username already exists",
            "model": ErrorResponse,
        },
    },
)
def register(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Register a new user account.

    Args:
        user_in: Registration payload (validated by Pydantic).
        db: Database session.

    Returns:
        AuthResponse with JWT token and user profile.
    """
    user, token, expires_in = register_user(db, user_in)
    return AuthResponse(
        token=TokenResponse(
            access_token=token,
            expires_in=expires_in,
        ),
        user=UserResponse.model_validate(user),
    )
