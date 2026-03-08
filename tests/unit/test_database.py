"""Unit tests for database helpers."""

import pytest
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.database import (
    clear_engine_cache,
    get_engine,
    get_session_factory,
)

pytestmark = pytest.mark.unit


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
