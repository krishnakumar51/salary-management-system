from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    if s.is_production:
        # Serverless: each invocation may be a fresh process and Neon's pooler
        # (PgBouncer, transaction mode) owns pooling, so don't pool twice. Also disable
        # server-side prepared statements, which PgBouncer transaction mode cannot track.
        return create_engine(
            s.database_url,
            poolclass=NullPool,
            connect_args={"prepare_threshold": None},
        )
    return create_engine(s.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = _session_factory()()
    try:
        yield db
    finally:
        db.close()
