"""Driver/Neon compatibility rules (pure functions; no database needed)."""

import ssl

from app.core.config import Settings
from app.db.engine import engine_options, is_pooled

NEON_POOLED = "postgresql+psycopg://u:p@ep-abc-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
NEON_DIRECT = NEON_POOLED.replace("-pooler", "")


def test_pooler_host_is_detected():
    assert is_pooled(NEON_POOLED) and not is_pooled(NEON_DIRECT)


def test_psycopg_pooled_disables_prepared_statements_and_keeps_libpq_options():
    url, kw = engine_options(NEON_POOLED)
    assert kw == {"connect_args": {"prepare_threshold": None}}
    assert url.query["sslmode"] == "require" and url.query["channel_binding"] == "require"


def test_psycopg_direct_needs_no_special_arguments():
    _, kw = engine_options(NEON_DIRECT)
    assert kw == {}


def test_pg8000_gets_a_verifying_tls_context_and_loses_libpq_only_options():
    url, kw = engine_options(NEON_POOLED.replace("+psycopg", "+pg8000"))
    ctx = kw["connect_args"]["ssl_context"]
    assert isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert "sslmode" not in url.query and "channel_binding" not in url.query
    assert "prepare_threshold" not in kw["connect_args"]


def test_pg8000_without_sslmode_stays_plaintext_for_local_databases():
    _, kw = engine_options("postgresql+pg8000://u:p@localhost/db")
    assert kw == {}


def test_plain_postgres_urls_are_normalised_to_psycopg_and_direct_url_is_optional():
    s = Settings(database_url="postgres://u:p@h/db", jwt_secret="x" * 20, database_url_direct="")
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.database_url_direct is None
    assert s.migration_database_url == s.database_url
    s2 = Settings(database_url="postgresql://u:p@h-pooler/db", database_url_direct="postgresql://u:p@h/db", jwt_secret="x" * 20)
    assert s2.migration_database_url == "postgresql+psycopg://u:p@h/db"
