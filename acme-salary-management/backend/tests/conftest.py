"""Test fixtures. Tests run against a REAL PostgreSQL (percentile_cont, row locks, triggers and
NUMERIC semantics matter), never SQLite.

* Set TEST_DATABASE_URL to use an existing Postgres (CI, docker-compose).
* Otherwise an embedded Postgres is started via the `pgserver` dev dependency.
"""

import atexit
import os
import tempfile
from datetime import date

import pytest

_server = None
url = os.environ.get("TEST_DATABASE_URL")
if not url:
    import pgserver

    _server = pgserver.get_server(tempfile.mkdtemp(prefix="acme_pg_"), cleanup_mode="stop")
    atexit.register(_server.cleanup)
    url = _server.get_uri()



def _ensure_psycopg() -> None:
    """Locked-down machines (e.g. Windows Application Control) may block psycopg's compiled
    `pq` module. Fall back to psycopg's pure-Python implementation + the libpq DLL that ships
    with pgserver. No effect when the normal import works."""
    try:
        import psycopg  # noqa: F401
        return
    except ImportError:
        pass
    import sys

    for name in [m for m in sys.modules if m == "psycopg" or m.startswith("psycopg.")]:
        del sys.modules[name]
    os.environ["PSYCOPG_IMPL"] = "python"
    if _server is not None:
        import pgserver

        bin_dir = os.path.join(os.path.dirname(pgserver.__file__), "pginstall", "bin")
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(bin_dir)


_ensure_psycopg()
os.environ["DATABASE_URL"] = url
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["APP_ENV"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.security import create_access_token  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Country, Department, Employee  # noqa: E402
from seed.reference import ensure_reference_data, ensure_user  # noqa: E402

TEST_PASSWORD = "Test-Passw0rd!"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean_db(_schema):
    engine = get_engine()
    with engine.begin() as conn:
        names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db():
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


@pytest.fixture
def ref(db):
    """Countries, departments, exchange rates and one HR user."""
    ensure_reference_data(db)
    user = ensure_user(db, "hr@acme-demo.com", TEST_PASSWORD, "Hannah HR")
    db.commit()
    return {"user": user}


@pytest.fixture
def user(ref):
    return ref["user"]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def ids(db, ref):
    countries = {c.code: c.id for c in db.query(Country)}
    departments = {d.name: d.id for d in db.query(Department)}
    return {"country": countries, "department": departments}


@pytest.fixture
def make_employee(client, auth, ids):
    """Creates an employee through the public API and returns its JSON."""
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        n = counter["n"]
        payload = {
            "first_name": f"Test{n}",
            "last_name": f"Person{n}",
            "email": f"test{n}@acme-demo.com",
            "country_id": ids["country"]["IN"],
            "department_id": ids["department"]["Engineering"],
            "designation": "Software Engineer",
            "employment_type": "full_time",
            "joining_date": "2022-01-10",
            "compensation": {"amount": "1500000.00", "currency": "INR", "frequency": "annual"},
        }
        payload.update(overrides)
        r = client.post("/api/v1/employees", json=payload, headers=auth)
        assert r.status_code == 201, r.text
        return r.json()

    return _make


def employee_count(db) -> int:
    return db.query(Employee).count()


TODAY = date.today().isoformat()
