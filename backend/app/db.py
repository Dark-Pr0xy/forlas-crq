"""Database engine and session management.

SQLite is configured with WAL journaling, NORMAL synchronous, and a generous
busy_timeout so concurrent reads during long simulations don't trip writers.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.config import settings

_engine: Engine | None = None


def _on_connect(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
            future=True,
        )
        event.listen(_engine, "connect", _on_connect)
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a SQLModel Session."""
    with Session(get_engine()) as session:
        yield session
