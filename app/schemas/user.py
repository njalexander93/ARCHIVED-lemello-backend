"""Pydantic v2 schemas for User operations.

Schema separation provides structural safety: hashed_password
cannot appear in API responses because it does not exist in
the UserResponse model.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import Self

# Username validation constants
USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

RESERVED_USERNAMES: frozenset[str] = frozenset(
    {
        # System routes
        "admin",
        "api",
        "login",
        "logout",
        "register",
        "settings",
        "profile",
        "account",
        "dashboard",
        "health",
        "status",
        "help",
        "support",
        # Technical
        "null",
        "undefined",
        "root",
        "system",
        "bot",
        "moderator",
        "mod",
        "superuser",
        # Platform-specific
        "lemello",
        "souschef",
        "recipe",
        "recipes",
        "chef",
        "kitchen",
        "explore",
        "feed",
        "search",
    }
)


class UserBase(BaseModel):
    """Shared fields for user schemas."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=30)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> str:
        """Normalize email to lowercase."""
        if not isinstance(value, str):
            raise ValueError("Email must be a string.")
        return value.lower().strip()

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: Any) -> str:
        """Validate and normalize username.

        Rules:
        - Lowercase ASCII only: [a-z0-9_-]
        - Must start with a letter
        - Must not be a reserved system name

        Args:
            value: The username string to validate.

        Returns:
            Normalized lowercase username.

        Raises:
            ValueError: If username is invalid or reserved.
        """
        if not isinstance(value, str):
            raise ValueError("Username must be a string.")
        normalized = value.lower().strip()
        if not USERNAME_PATTERN.match(normalized):
            raise ValueError(
                "Username must start with a letter and "
                "contain only lowercase letters, numbers, "
                "underscores, and hyphens."
            )
        if normalized in RESERVED_USERNAMES:
            raise ValueError(f"The username '{normalized}' is reserved.")
        return normalized


class UserCreate(UserBase):
    """Schema for user registration requests.

    Validates password strength and confirmation match.
    """

    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    password_confirm: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Enforce password complexity requirements.

        Requires at least one uppercase letter, one lowercase
        letter, and one digit.

        Args:
            value: The password string to validate.

        Returns:
            The validated password string.

        Raises:
            ValueError: If password does not meet complexity
                requirements.
        """
        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "Password must contain at least one uppercase letter."
            )
        if not re.search(r"[a-z]", value):
            raise ValueError(
                "Password must contain at least one lowercase letter."
            )
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        return value

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        """Verify password and password_confirm are identical.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If passwords do not match.
        """
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match.")
        return self


class UserResponse(BaseModel):
    """Schema for user data in API responses.

    Structural safety: hashed_password is not defined here,
    so it cannot leak in responses even if the developer
    forgets to exclude it manually.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    is_active: bool
    email_verified_at: datetime | None
    role: str
    preferences: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None


class UserUpdate(BaseModel):
    """Schema for partial user profile updates.

    All fields are optional. Only provided fields are updated.
    """

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=30)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        """Normalize email to lowercase if provided."""
        if value is not None:
            return value.lower().strip()
        return value

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        """Validate and normalize username if provided.

        Args:
            value: The username string to validate, or None.

        Returns:
            Normalized lowercase username, or None.

        Raises:
            ValueError: If username is invalid or reserved.
        """
        if value is None:
            return value
        normalized = value.lower().strip()
        if not USERNAME_PATTERN.match(normalized):
            raise ValueError(
                "Username must start with a letter and "
                "contain only lowercase letters, numbers, "
                "underscores, and hyphens."
            )
        if normalized in RESERVED_USERNAMES:
            raise ValueError(f"The username '{normalized}' is reserved.")
        return normalized


class UserInDB(UserResponse):
    """Internal schema with sensitive fields.

    Used only within the application layer, never in API
    responses. Extends UserResponse with authentication
    fields needed for login and token validation.
    """

    hashed_password: str | None
    password_changed_at: datetime | None
