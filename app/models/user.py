"""SQLAlchemy ORM model for user accounts."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UUIDMixin:
    """Mixin providing a UUIDv7 primary key.

    Uses Python 3.14's stdlib uuid.uuid7() for time-ordered,
    B-tree-friendly primary keys. Generated application-side
    because PostgreSQL 16 has no native UUIDv7 function.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
    )


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps.

    Uses TIMESTAMPTZ (timezone=True) for unambiguous UTC storage.
    Server defaults ensure consistency for non-ORM inserts.
    Python defaults provide values for in-memory instances
    before database flush (useful in tests).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(UUIDMixin, TimestampMixin, Base):
    """User account model.

    Stores identity, authentication, and personalization data.
    Supports soft-delete via deleted_at timestamp.

    Attributes:
        id: UUIDv7 primary key (from UUIDMixin).
        email: Unique email, stored lowercase.
        username: Unique username, stored lowercase, ASCII-only.
        hashed_password: Argon2id hash. Nullable for future OAuth users.
        password_changed_at: Tracks last password change for JWT invalidation.
        is_active: Account enabled flag. False blocks login.
        email_verified_at: Timestamp of email verification.
        role: Authorization role. Default 'user'.
        preferences: JSONB personalization settings.
        deleted_at: Soft-delete timestamp. None means active.
        created_at: Row creation time (from TimestampMixin).
        updated_at: Last modification time (from TimestampMixin).
    """

    __tablename__ = "users"

    # Identity
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(30), nullable=False)

    # Authentication
    hashed_password: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        default=True,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        server_default=text("'user'"),
        default="user",
    )

    # AI personalization
    preferences: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON().with_variant(JSONB, "postgresql")),
        server_default=text("'{}'::jsonb"),
        default=dict,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_users_email_lower",
            text("LOWER(email)"),
            unique=True,
        ),
        Index(
            "ix_users_username_lower",
            text("LOWER(username)"),
            unique=True,
        ),
    )

    @property
    def is_verified(self) -> bool:
        """Check if user's email has been verified."""
        return self.email_verified_at is not None

    @property
    def is_deleted(self) -> bool:
        """Check if user account has been soft-deleted."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        """Return string representation of User."""
        return (
            f"<User(id={self.id!r}, "
            f"username={self.username!r}, "
            f"email={self.email!r})>"
        )
