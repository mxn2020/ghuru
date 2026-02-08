"""Database engine and session helpers for gh-agent-funhouse."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from gh_agent_funhouse.config import get_db_path
from gh_agent_funhouse.db.models import Base

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy engine backed by the local SQLite DB."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        db_path = get_db_path()
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)
    return _engine


def get_session() -> Session:
    """Return a new SQLAlchemy session bound to the default engine."""
    return Session(bind=get_engine())


def init_db() -> None:
    """Create all tables that do not yet exist."""
    Base.metadata.create_all(get_engine())
