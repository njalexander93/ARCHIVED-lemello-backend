"""Unit tests for the User ORM model."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User

pytestmark = pytest.mark.unit


def test_user_defaults(db_session: Session) -> None:
    """User defaults are applied on flush."""
    user = User(
        email="chef@lemello.com",
        username="chef",
        hashed_password="hashed-value",
    )

    db_session.add(user)
    db_session.flush()

    assert isinstance(user.id, uuid.UUID)
    assert user.id.version == 7
    assert user.is_active is True
    assert user.role == "user"
    assert user.preferences == {}
    assert user.email_verified_at is None
    assert user.deleted_at is None
    assert user.password_changed_at is None


def test_is_verified_property() -> None:
    """is_verified reflects email_verified_at state."""
    user = User(
        email="verified@lemello.com",
        username="verified_user",
        hashed_password="hashed-value",
    )
    assert user.is_verified is False

    user.email_verified_at = datetime.now(UTC)
    assert user.is_verified is True


def test_is_deleted_property() -> None:
    """is_deleted reflects deleted_at state."""
    user = User(
        email="active@lemello.com",
        username="active_user",
        hashed_password="hashed-value",
    )
    assert user.is_deleted is False

    user.deleted_at = datetime.now(UTC)
    assert user.is_deleted is True


def test_hashed_password_nullable(db_session: Session) -> None:
    """Users can be created with a null hashed password."""
    user = User(
        email="oauth@lemello.com",
        username="oauth_user",
        hashed_password=None,
    )

    db_session.add(user)
    db_session.flush()

    assert user.hashed_password is None


def test_user_persistence(db_session: Session) -> None:
    """A persisted user can be queried by id."""
    user = User(
        email="persist@lemello.com",
        username="persist_user",
        hashed_password="hashed-value",
    )

    db_session.add(user)
    db_session.flush()

    loaded = db_session.scalar(select(User).where(User.id == user.id))

    assert loaded is not None
    assert loaded.id == user.id
    assert loaded.email == "persist@lemello.com"


def test_unique_email_constraint(db_session: Session) -> None:
    """Case-insensitive duplicate email values violate uniqueness."""
    first = User(
        email="Duplicate@lemello.com",
        username="first_user",
        hashed_password="hashed-value",
    )
    second = User(
        email="duplicate@lemello.com",
        username="second_user",
        hashed_password="hashed-value",
    )

    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_unique_username_constraint(db_session: Session) -> None:
    """Case-insensitive duplicate username values violate uniqueness."""
    first = User(
        email="first@lemello.com",
        username="Dupe_User",
        hashed_password="hashed-value",
    )
    second = User(
        email="second@lemello.com",
        username="dupe_user",
        hashed_password="hashed-value",
    )

    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_preferences_mutation_tracking(db_session: Session) -> None:
    """In-place JSON mutations are tracked by SQLAlchemy."""
    user = User(
        email="prefs@lemello.com",
        username="prefs_user",
        hashed_password="hashed-value",
    )

    db_session.add(user)
    db_session.flush()

    user.preferences["theme"] = "dark"

    assert db_session.is_modified(user, include_collections=True) is True
