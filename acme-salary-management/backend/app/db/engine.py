"""Single place that turns a database URL into a SQLAlchemy engine.

Used by the web app, Alembic and the seed script so Neon compatibility lives in one spot.

Drivers (selected by the URL scheme):
  postgresql://...            -> psycopg 3 (default; what Vercel uses)
  postgresql+pg8000://...     -> pure-Python fallback for machines that cannot load psycopg's
                                 compiled/libpq libraries (e.g. Windows Application Control).

Neon specifics handled here:
  * "-pooler" hosts are PgBouncer (transaction mode): server-side prepared statements are disabled.
  * psycopg understands libpq URL options (sslmode, channel_binding). pg8000 does not, so for it
    `sslmode=require|verify-*` becomes a verifying TLS context and libpq-only options are dropped.
"""

import ssl

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url

_LIBPQ_ONLY_OPTIONS = ("sslmode", "channel_binding", "options", "sslrootcert", "target_session_attrs")
_TLS_MODES = {"require", "verify-ca", "verify-full"}


def is_pooled(url: str | URL) -> bool:
    host = make_url(url).host or ""
    return "-pooler" in host


def engine_options(url: str | URL) -> tuple[URL, dict]:
    """Returns (url, create_engine kwargs) adjusted for the URL's driver and for pooling."""
    u = make_url(url)
    connect_args: dict = {}
    if u.drivername.endswith("+pg8000"):
        mode = str(u.query.get("sslmode", "")).lower()
        if mode in _TLS_MODES:
            connect_args["ssl_context"] = ssl.create_default_context()
        u = u.set(query={k: v for k, v in u.query.items() if k not in _LIBPQ_ONLY_OPTIONS})
    elif is_pooled(u):
        connect_args["prepare_threshold"] = None  # psycopg only; PgBouncer can't track prepared statements
    return u, {"connect_args": connect_args} if connect_args else {}


def build_engine(url: str | URL, **kwargs) -> Engine:
    u, extra = engine_options(url)
    return create_engine(u, **{**extra, **kwargs})
