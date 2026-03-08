"""Authentication service layer."""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictException
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)

CONSTRAINT_TO_FIELD: dict[str, str] = {
    "ix_users_email_lower": "email",
    "ix_users_username_lower": "username",
}


def _identify_duplicate_field(exc: IntegrityError) -> str:
    """Extract the conflicting field from a unique constraint violation.

    Uses psycopg3 diagnostics when available (production with
    PostgreSQL), falls back to string matching (SQLite in tests).

    Args:
        exc: The IntegrityError raised by SQLAlchemy.

    Returns:
        The name of the conflicting field, or a generic fallback.
    """
    if exc.orig is not None and hasattr(exc.orig, "diag"):
        constraint = getattr(exc.orig.diag, "constraint_name", None)
        if constraint and constraint in CONSTRAINT_TO_FIELD:
            return CONSTRAINT_TO_FIELD[constraint]

    msg = str(exc.orig) if exc.orig else str(exc)
    for constraint_name, field in CONSTRAINT_TO_FIELD.items():
        if constraint_name in msg:
            return field
    if "users.email" in msg.lower():
        return "email"
    if "users.username" in msg.lower():
        return "username"
    return "email or username"


def register_user(
    db: Session,
    user_in: UserCreate,
) -> tuple[User, str, int]:
    """Register a new user account.

    Creates the user, hashes the password, persists to database,
    and generates a JWT access token.

    Args:
        db: Database session (transaction managed by get_db).
        user_in: Validated registration payload.

    Returns:
        Tuple of (created User, JWT token string, expires_in seconds).

    Raises:
        ConflictException: If email or username is already taken.
    """
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )

    try:
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError as exc:
        field = _identify_duplicate_field(exc)
        logger.warning(
            "Registration conflict",
            extra={"field": field},
        )
        raise ConflictException(
            detail=f"A user with this {field} already exists.",
        ) from exc

    logger.info(
        "User registered",
        extra={"user_id": str(user.id)},
    )

    token = create_access_token(user_id=user.id)
    expires_in = settings.access_token_expire_minutes * 60

    return user, token, expires_in
