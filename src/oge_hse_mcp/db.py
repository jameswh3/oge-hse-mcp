from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from oge_hse_mcp.config import get_settings
from oge_hse_mcp.models import Base


@lru_cache(maxsize=8)
def _engine(database_url: str):
    kwargs = {}
    if database_url.endswith(":memory:"):
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    return create_engine(database_url, **kwargs)


def ensure_schema(database_url: str | None = None) -> None:
    Base.metadata.create_all(_engine(database_url or get_settings().database_url))


@contextmanager
def session_scope() -> Iterator[Session]:
    engine = _engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
