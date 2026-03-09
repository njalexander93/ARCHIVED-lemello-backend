"""Unit tests for database helpers."""

from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine

from app.core import database as database_module
from app.core.config import settings
from app.core.database import (
    clear_engine_cache,
    get_engine,
    get_session_factory,
)

pytestmark = pytest.mark.unit


class SessionSpy:
    """Minimal session test double for get_db() transaction tests."""

    def __init__(self, *, commit_error: Exception | None = None) -> None:
        """Initialize the session spy."""
        self.commit_error = commit_error
        self.commit_called = False
        self.rollback_called = False
        self.close_called = False

    def commit(self) -> None:
        """Record commit calls and optionally raise a test exception."""
        self.commit_called = True
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        """Record rollback calls."""
        self.rollback_called = True

    def close(self) -> None:
        """Record close calls."""
        self.close_called = True


@pytest.fixture(autouse=True)
def _reset_engine_cache() -> None:
    """Reset cached engine between tests for isolation."""
    clear_engine_cache()
    yield
    clear_engine_cache()


def test_get_engine_uses_url_argument() -> None:
    """Engine uses the explicit URL argument when provided."""
    engine = get_engine("sqlite+pysqlite:///:memory:")
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "sqlite+pysqlite"


def test_get_engine_uses_settings_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Engine falls back to settings.database_url when url is None."""
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "app_debug", False)
    engine = get_engine()
    assert engine.url.drivername == "sqlite+pysqlite"


def test_get_engine_respects_app_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Engine echo follows settings.app_debug."""
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "app_debug", True)
    engine = get_engine()
    assert engine.echo is True


def test_get_engine_raises_when_missing_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing settings.database_url should raise a clear error."""
    monkeypatch.setattr(settings, "database_url", None)
    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        get_engine()


def test_get_session_factory_configuration() -> None:
    """Session factory uses expire_on_commit=False and binds an engine."""
    factory = get_session_factory("sqlite+pysqlite:///:memory:")
    session = factory()
    try:
        assert session.expire_on_commit is False
        bind = session.get_bind()
        assert isinstance(bind, Engine)
    finally:
        session.close()


def test_get_engine_reuses_cached_instance_for_same_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same DB settings should return the same cached engine."""
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "app_debug", False)
    first = get_engine()
    second = get_engine()
    assert first is second


def test_get_engine_cache_varies_by_debug_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing app_debug should produce a distinct cached engine key."""
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "app_debug", False)
    first = get_engine()
    monkeypatch.setattr(settings, "app_debug", True)
    second = get_engine()
    assert first is not second


def test_clear_engine_cache_resets_cached_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clearing cache should force a fresh engine creation."""
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "app_debug", False)
    first = get_engine()
    clear_engine_cache()
    second = get_engine()
    assert first is not second


def test_get_db_commits_after_successful_yield(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_db commits after successful request handling."""
    session = SessionSpy()
    monkeypatch.setattr(
        database_module,
        "get_session_factory",
        lambda url=None: lambda: session,
    )

    generator = database_module.get_db()

    assert next(generator) is session

    with pytest.raises(StopIteration):
        next(generator)

    assert session.commit_called is True
    assert session.rollback_called is False
    assert session.close_called is True


def test_get_db_rolls_back_when_consumer_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_db rolls back when the dependency consumer raises."""
    session = SessionSpy()
    monkeypatch.setattr(
        database_module,
        "get_session_factory",
        lambda url=None: lambda: session,
    )

    generator = database_module.get_db()

    assert next(generator) is session

    with pytest.raises(RuntimeError, match="boom"):
        generator.throw(RuntimeError("boom"))

    assert session.commit_called is False
    assert session.rollback_called is True
    assert session.close_called is True


def test_get_db_closes_session_when_commit_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_db closes the session even if commit itself fails."""
    session = SessionSpy(commit_error=RuntimeError("commit failed"))
    monkeypatch.setattr(
        database_module,
        "get_session_factory",
        lambda url=None: lambda: session,
    )

    generator = database_module.get_db()

    assert next(generator) is session

    with pytest.raises(RuntimeError, match="commit failed"):
        next(generator)

    assert session.commit_called is True
    assert session.rollback_called is True
    assert session.close_called is True
