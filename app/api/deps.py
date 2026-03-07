"""FastAPI dependency injection for authentication and authorization."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidSignatureError,
    InvalidTokenError,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Extract and validate JWT, then load the authenticated user.

    Performs five checks in sequence:
    1. Cryptographic token validation (signature, expiration, required claims)
    2. Claim extraction into typed TokenPayload
    3. User existence in database
    4. Soft-delete and active status
    5. Password-change invalidation (iat vs password_changed_at)

    Args:
        token: JWT string extracted from Authorization: Bearer header.
        db: Database session.

    Returns:
        The authenticated User ORM instance.

    Raises:
        HTTPException: 401 for invalid/expired/revoked tokens or missing users.
        HTTPException: 403 for inactive users.
    """
    try:
        token_data = verify_token(token)
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (
        DecodeError,
        InvalidSignatureError,
        InvalidAlgorithmError,
        InvalidTokenError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_INVALID",
                "message": "Could not validate token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_INVALID",
                "message": "Could not validate token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, user_id)

    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USER_INACTIVE",
                "message": "User account is inactive",
            },
        )

    if user.password_changed_at is not None and token_data.iat <= int(
        user.password_changed_at.timestamp()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_REVOKED",
                "message": "Token invalidated by password change",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Like get_current_user, but returns None when no token is provided.

    If a token is provided but invalid, this still raises 401.

    Args:
        token: Optional JWT string. None if no Authorization header.
        db: Database session.

    Returns:
        The authenticated User, or None if no token was provided.
    """
    if token is None:
        return None
    return get_current_user(token=token, db=db)


class RoleChecker:
    """Dependency class for role-based endpoint protection."""

    def __init__(self, allowed_roles: list[str]) -> None:
        """Initialize role checker.

        Args:
            allowed_roles: Roles allowed to access the endpoint.
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Verify the authenticated user has an allowed role.

        Args:
            current_user: The authenticated user from get_current_user.

        Returns:
            The user if their role is allowed.

        Raises:
            HTTPException: 403 if the user's role is not in allowed_roles.
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": (
                        "You do not have permission to access this resource"
                    ),
                },
            )
        return current_user


require_admin = RoleChecker(["admin"])
require_user = RoleChecker(["user", "admin"])
