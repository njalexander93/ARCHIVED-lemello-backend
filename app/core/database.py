"""SQLAlchemy database engine and session configuration.

Provides the declarative base class for ORM models and
factory functions for creating database engines and sessions.
All domain models must inherit from Base to be detected by
Alembic autogenerate.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    All domain models must inherit from this class to ensure
    their tables are registered in Base.metadata and visible
    to Alembic's autogenerate.
    """

    pass


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    Args:
        url: Database URL. Defaults to settings.database_url.

    Returns:
        A SQLAlchemy Engine instance.

    Raises:
        ValueError: If no database URL is configured.
    """
    db_url = url or settings.database_url
    if not db_url:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set it in .env or as an environment variable."
        )
    return create_engine(db_url, echo=settings.app_debug)


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Create a session factory bound to an engine.

    Args:
        url: Database URL. Defaults to settings.database_url.

    Returns:
        A sessionmaker instance for creating database sessions.
    """
    engine = get_engine(url)
    return sessionmaker(bind=engine, expire_on_commit=False)
