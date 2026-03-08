"""SQLAlchemy database engine and session configuration.

Provides the declarative base class for ORM models and
factory functions for creating database engines and sessions.
All domain models must inherit from Base to be detected by
Alembic autogenerate.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_engine_cache_key: tuple[str, bool] | None = None
_engine_cache_instance: Engine | None = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All domain models must inherit from this class to ensure
    their tables are registered in Base.metadata and visible
    to Alembic's autogenerate.

    Uses a naming convention so all constraints have predictable,
    referenceable names for Alembic migrations.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _resolve_database_url(url: str | None = None) -> str:
    """Resolve the database URL from explicit arg or settings."""
    db_url = url or settings.database_url
    if not db_url:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set it in .env or as an environment variable."
        )
    return db_url


def _managed_engine(db_url: str, debug: bool) -> Engine:
    """Return cached engine for active key, disposing stale engine on swap."""
    global _engine_cache_instance, _engine_cache_key

    cache_key = (db_url, debug)
    if _engine_cache_key != cache_key:
        if _engine_cache_instance is not None:
            _engine_cache_instance.dispose()
        _engine_cache_instance = create_engine(db_url, echo=debug)
        _engine_cache_key = cache_key

    if _engine_cache_instance is None:
        _engine_cache_instance = create_engine(db_url, echo=debug)
        _engine_cache_key = cache_key
    return _engine_cache_instance


def clear_engine_cache() -> None:
    """Dispose and clear the cached engine instance."""
    global _engine_cache_instance, _engine_cache_key

    if _engine_cache_instance is not None:
        _engine_cache_instance.dispose()
    _engine_cache_instance = None
    _engine_cache_key = None


def get_engine(url: str | None = None) -> Engine:
    """Get a SQLAlchemy engine.

    Args:
        url: Database URL. Defaults to settings.database_url.

    Returns:
        A SQLAlchemy Engine instance.

    Raises:
        ValueError: If no database URL is configured.
    """
    db_url = _resolve_database_url(url)
    # Reuse per-config engine and dispose stale engine when key changes.
    return _managed_engine(db_url, settings.app_debug)


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Get a session factory bound to an engine.

    Args:
        url: Database URL. Defaults to settings.database_url.

    Returns:
        A sessionmaker instance for creating database sessions.

    Raises:
        ValueError: If no database URL is configured.
    """
    engine = get_engine(url)
    # Avoid expiring instances on commit in request-scoped usage.
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Yield a request-scoped database session.

    Yields:
        A SQLAlchemy Session instance.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
