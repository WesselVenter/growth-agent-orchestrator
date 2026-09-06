"""Postgres connection setup, using DATABASE_URL from the environment."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/growth_agent_orchestrator",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Session:
    """Return a new Session. Caller is responsible for closing it."""
    return SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager: commits on success, rolls back and re-raises on error.

    Use for any write that should be atomic:

        with session_scope() as session:
            session.add(SomeModel(...))
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
