"""Shared pytest fixtures for all tests.

This module contains fixtures that are available across all test suites
(unit, integration, and e2e tests).
"""

import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.main import app


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Create an in-memory SQLite engine for testing.

    Uses a static pool so all connections share the same
    in-memory database within the session scope.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_connection: sqlite3.Connection,
        connection_record: Any,
    ) -> None:
        """Enable SQLite foreign key enforcement."""
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Provide a transactional database session for tests.

    Each test runs inside a transaction that is rolled back
    after the test, ensuring test isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_nested_transaction(
        session_: Session,
        transaction_: SessionTransaction,
    ) -> None:
        """Restart SAVEPOINT after each nested transaction end."""
        parent = transaction_.parent
        if transaction_.nested and parent is not None and not parent.nested:
            session_.begin_nested()

    try:
        yield session
    finally:
        event.remove(
            session,
            "after_transaction_end",
            restart_nested_transaction,
        )
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    """Create a fresh TestClient for each test.

    Yields:
        TestClient configured with the FastAPI app.
    """
    with TestClient(app) as client:
        yield client
