"""Runs the read paths through the pure-Python pg8000 driver (the fallback used on machines where
psycopg is blocked). pg8000 sends every literal as a bind parameter, which exposes SQL that only
works when the driver happens to reuse a parameter (e.g. SELECT vs GROUP BY expressions).
"""

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("pg8000")

from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.engine import build_engine  # noqa: E402
from app.repositories import employees as emp_repo  # noqa: E402
from app.services import analytics, currency as fx  # noqa: E402
from tests.factories import add_employee  # noqa: E402


@pytest.fixture
def pg8000_session():
    url = get_settings().database_url.replace("+psycopg", "+pg8000")
    engine = build_engine(url)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def data(db, ids, client, auth):
    add_employee(db, ids, 1, country="IN", amount="6660000", currency="INR")
    add_employee(db, ids, 2, country="US", department="Sales", amount="200000", currency="USD")
    e = add_employee(db, ids, 3, country="DE", amount="4700", currency="EUR", frequency="monthly")
    from app.models import Compensation

    cid = db.query(Compensation).filter_by(employee_id=e.id).one().id
    for d, pct in (("2026-03-01", "10"), ("2026-05-01", "5")):
        r = client.post(
            f"/api/v1/compensation/{cid}/increment",
            json={"type": "percentage", "value": pct, "effective_date": d, "reason": "Review"},
            headers=auth,
        )
        assert r.status_code == 200, r.text


def test_every_analytics_query_runs_on_pg8000(pg8000_session, data):
    s = pg8000_session
    d = analytics.dashboard(s, "USD")
    assert d.total_employees == 3 and d.overall.count == 3
    assert [t.currency for t in d.totals_by_currency] == ["EUR", "INR", "USD"]
    assert len(analytics.by_group(s, "EUR", "department").groups) == 2
    assert len(analytics.by_group(s, "INR", "country").groups) == 3
    assert sum(b.count for b in analytics.distribution(s, "USD", None, None).bands) == 3
    assert analytics.currencies(s, "USD").items


def test_trends_group_by_month_on_pg8000(pg8000_session, data):
    pts = analytics.trends(pg8000_session, "USD").points
    assert [(p.month, p.changes) for p in pts] == [("2026-03", 1), ("2026-05", 1)]
    assert pts[0].average_increment_percentage == Decimal("10.00")


def test_directory_search_filters_and_salary_sort_on_pg8000(pg8000_session, data):
    rates = fx.rates_to_reporting(fx.load_snapshot(pg8000_session), "USD")
    items, total = emp_repo.search(
        pg8000_session,
        emp_repo.EmployeeFilters(q="emp", salary_min=Decimal(50000)),
        sort="salary", descending=True, page=1, page_size=10, rates=rates,
    )
    assert total == 3 and items[0].email == "emp2@acme-demo.com"  # USD 200,000 is highest
    assert date(2021, 3, 1) == items[0].joining_date


def test_conversion_keeps_full_rate_precision_on_pg8000(pg8000_session, db, ids):
    """Regression: pg8000 rounded the bound exchange rate to 2 decimals (0.012012 -> 0.01), so every
    INR->USD figure was 17% too low and EUR->USD 0.2% too high."""
    add_employee(db, ids, 11, country="IN", amount="6660000", currency="INR")      # = USD 80,000.00
    add_employee(db, ids, 12, country="DE", amount="4700", currency="EUR", frequency="monthly")  # = USD 61,304.35
    d = analytics.dashboard(pg8000_session, "USD")
    by = {t.currency: t for t in d.totals_by_currency}
    assert by["INR"].total_annual_reporting == Decimal("80000.00")
    assert by["EUR"].total_annual_reporting == Decimal("61304.35")
    assert d.total_compensation_reporting == Decimal("141304.35")
    # and the directory salary filter/sort use the same precise rate
    rates = fx.rates_to_reporting(fx.load_snapshot(pg8000_session), "USD")
    _, total = emp_repo.search(
        pg8000_session, emp_repo.EmployeeFilters(salary_min=Decimal(79990), salary_max=Decimal(80010)),
        sort="salary", descending=True, page=1, page_size=10, rates=rates,
    )
    assert total == 1


def test_exact_edge_inclusion_on_pg8000(pg8000_session, db, ids):
    add_employee(db, ids, 21, country="DE", amount="46000", currency="EUR")  # exactly USD 50,000
    rates = fx.rates_to_reporting(fx.load_snapshot(pg8000_session), "USD")
    _, total = emp_repo.search(
        pg8000_session, emp_repo.EmployeeFilters(salary_min=Decimal(50000)),
        sort="salary", descending=True, page=1, page_size=10, rates=rates,
    )
    assert total == 1
