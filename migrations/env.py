"""Alembic migration environment configuration.

Integrates with Lemello's Pydantic Settings for database URL
injection and registers pgvector types for autogenerate support.
"""

from logging.config import fileConfig

import pgvector.sqlalchemy
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# Import application settings and Base metadata
from app.core.config import settings
from app.core.database import Base

# -------------------------------------------------------------------
# Future models must be imported here (or in database.py) so that
# Base.metadata includes their table definitions for autogenerate.
#
# Example:
#   from app.models.recipe import Recipe  # noqa: F401
#   from app.models.user import User  # noqa: F401
# -------------------------------------------------------------------
from app.models.user import User  # noqa: F401

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override alembic.ini placeholder with real URL from Pydantic Settings
database_url = settings.database_url
if not database_url:
    raise ValueError(
        "Database URL is not configured. "
        "Set a valid 'database_url' in app.core.config.Settings before "
        "running migrations."
    )
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Target metadata for autogenerate support
target_metadata = Base.metadata


def _register_pgvector_types(connection: Connection) -> None:
    """Register pgvector custom types in the PostgreSQL dialect.

    Without this, Alembic autogenerate will emit warnings like:
        SAWarning: Did not recognize type 'vector' of column 'embedding'
    and may generate incorrect migrations for vector columns.
    """
    dialect = connection.dialect
    if getattr(dialect, "name", None) != "postgresql":
        return
    ischema_names = getattr(dialect, "ischema_names", None)
    if ischema_names is None:
        return
    ischema_names["vector"] = pgvector.sqlalchemy.Vector
    # Register additional types for future use
    if hasattr(pgvector.sqlalchemy, "HALFVEC"):
        ischema_names["halfvec"] = pgvector.sqlalchemy.HALFVEC
    if hasattr(pgvector.sqlalchemy, "SPARSEVEC"):
        ischema_names["sparsevec"] = pgvector.sqlalchemy.SPARSEVEC


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL script output without connecting to the database.
    Useful for generating migration SQL for review.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Keep type comparisons on so pgvector column changes are detected.
        compare_type=True,
        compare_server_default=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a database connection and runs migrations within
    a transaction. Uses NullPool because migrations are
    short-lived — connection pooling adds overhead with no benefit.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # Migrations are short-lived; pooling does not buy much here.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Register pgvector types before configuring context
        _register_pgvector_types(connection)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Ensure Alembic emits diffs when column types change.
            compare_type=True,
            compare_server_default=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
