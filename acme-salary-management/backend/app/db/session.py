from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.engine import build_engine


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    if s.is_production:
        # Serverless: each invocation may be a fresh process and Neon's pooler (PgBouncer,
        # transaction mode) owns pooling, so don't pool twice. build_engine also turns off
        # server-side prepared statements for "-pooler" hosts.
        return build_engine(s.database_url, poolclass=NullPool)
    return build_engine(s.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = _session_factory()()
    try:
        yield db
    finally:
        db.close()
