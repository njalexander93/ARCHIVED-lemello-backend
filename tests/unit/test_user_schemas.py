"""Unit tests for user Pydantic schemas."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserResponse, UserUpdate

pytestmark = pytest.mark.unit


def test_user_create_valid_input() -> None:
    """Valid UserCreate payload validates successfully."""
    user = UserCreate(
        email="chef@lemello.com",
        username="souschef_1",
        password="StrongPass1",
        password_confirm="StrongPass1",
    )

    assert user.email == "chef@lemello.com"
    assert user.username == "souschef_1"


def test_email_normalization() -> None:
    """Email values are normalized to lowercase."""
    user = UserCreate(
        email="Chef@LEMELLO.com",
        username="souschef_1",
        password="StrongPass1",
        password_confirm="StrongPass1",
    )

    assert user.email == "chef@lemello.com"


def test_email_normalization_strips_whitespace() -> None:
    """Email normalization strips surrounding whitespace."""
    user = UserCreate(
        email="  Chef@LEMELLO.com  ",
        username="souschef_1",
        password="StrongPass1",
        password_confirm="StrongPass1",
    )

    assert user.email == "chef@lemello.com"


def test_username_normalization() -> None:
    """Username values are normalized to lowercase."""
    user = UserCreate(
        email="chef@lemello.com",
        username="SousChef_1",
        password="StrongPass1",
        password_confirm="StrongPass1",
    )

    assert user.username == "souschef_1"


def test_username_length_is_validated_after_normalization() -> None:
    """Username length constraints apply after whitespace stripping."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="chef@lemello.com",
            username="ab ",
            password="StrongPass1",
            password_confirm="StrongPass1",
        )


def test_invalid_email_format() -> None:
    """Invalid email format raises ValidationError."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            username="souschef_1",
            password="StrongPass1",
            password_confirm="StrongPass1",
        )


def test_reserved_username() -> None:
    """Reserved username values are rejected."""
    with pytest.raises(ValidationError, match="reserved"):
        UserCreate(
            email="chef@lemello.com",
            username="admin",
            password="StrongPass1",
            password_confirm="StrongPass1",
        )


def test_username_invalid_characters() -> None:
    """Usernames with invalid characters are rejected."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="chef@lemello.com",
            username="user@name",
            password="StrongPass1",
            password_confirm="StrongPass1",
        )


def test_username_starts_with_number() -> None:
    """Usernames must start with a letter."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="chef@lemello.com",
            username="1chef",
            password="StrongPass1",
            password_confirm="StrongPass1",
        )


def test_password_too_short() -> None:
    """Password shorter than minimum length is rejected."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="chef@lemello.com",
            username="souschef_1",
            password="Short1A",
            password_confirm="Short1A",
        )


def test_password_missing_uppercase() -> None:
    """Passwords must include an uppercase letter."""
    with pytest.raises(ValidationError, match="uppercase"):
        UserCreate(
            email="chef@lemello.com",
            username="souschef_1",
            password="alllowercase1",
            password_confirm="alllowercase1",
        )


def test_password_missing_lowercase() -> None:
    """Passwords must include a lowercase letter."""
    with pytest.raises(ValidationError, match="lowercase"):
        UserCreate(
            email="chef@lemello.com",
            username="souschef_1",
            password="ALLUPPERCASE1",
            password_confirm="ALLUPPERCASE1",
        )


def test_password_missing_digit() -> None:
    """Passwords must include at least one digit."""
    with pytest.raises(ValidationError, match="digit"):
        UserCreate(
            email="chef@lemello.com",
            username="souschef_1",
            password="NoDigitsHere",
            password_confirm="NoDigitsHere",
        )


def test_password_confirmation_mismatch() -> None:
    """Password and confirmation must match."""
    with pytest.raises(ValidationError, match="do not match"):
        UserCreate(
            email="chef@lemello.com",
            username="souschef_1",
            password="StrongPass1",
            password_confirm="StrongPass2",
        )


def test_user_response_from_attributes() -> None:
    """UserResponse can be built from attribute-based objects."""
    now = datetime.now(UTC)
    orm_obj = SimpleNamespace(
        id=uuid.uuid7(),
        email="chef@lemello.com",
        username="souschef_1",
        is_active=True,
        email_verified_at=None,
        role="user",
        preferences={},
        created_at=now,
        updated_at=now,
        hashed_password="should_not_leak",
    )

    response = UserResponse.model_validate(orm_obj)

    dumped = response.model_dump()
    assert dumped["email"] == "chef@lemello.com"
    assert "hashed_password" not in dumped


def test_user_update_partial() -> None:
    """UserUpdate supports partial updates."""
    update = UserUpdate(email="Chef@LEMELLO.com")

    assert update.email == "chef@lemello.com"
    assert update.username is None
