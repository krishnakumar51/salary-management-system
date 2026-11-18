from datetime import date
from decimal import Decimal

import pytest

from tests.factories import add_employee

A = "/api/v1/analytics"


@pytest.fixture
def population(db, ids):
    # Rates: 1 USD = 83.25 INR = 0.92 EUR. Values avoid band edges so rounding noise can't matter.
    add_employee(db, ids, 1, country="IN", department="Engineering", amount="6660000", currency="INR")  # 80,000 USD
    add_employee(db, ids, 2, country="US", department="Engineering", amount="200000", currency="USD")
    add_employee(db, ids, 3, country="DE", department="Engineering", amount="4700", currency="EUR",
                 frequency="monthly")  # 56,400 EUR = 61,304.35 USD
    add_employee(db, ids, 4, country="US", department="Sales", amount="50000", currency="USD",
                 status="on_leave")
    add_employee(db, ids, 5, country="US", department="Sales", amount="999999", currency="USD",
                 status="terminated")  # excluded from compensation analytics
    add_employee(db, ids, 6, country="CA", department="Sales", amount=None)  # no compensation


def test_dashboard_headcounts_come_from_database(client, auth, population):
    d = client.get(f"{A}/dashboard", params={"currency": "USD"}, headers=auth).json()
    assert d["total_employees"] == 6
    assert d["active_employees"] == 4
    assert d["employees_without_compensation"] == 1
    assert {c["label"]: c["count"] for c in d["by_country"]} == {
        "United States": 3, "India": 1, "Germany": 1, "Canada": 1
    }
    assert {c["label"]: c["count"] for c in d["by_status"]} == {"active": 4, "on_leave": 1, "terminated": 1}
    assert {c["label"]: c["count"] for c in d["by_department"]} == {"Engineering": 3, "Sales": 3}


def test_totals_by_currency_are_not_mixed_and_reporting_total_is_converted(client, auth, population):
    d = client.get(f"{A}/dashboard", params={"currency": "USD"}, headers=auth).json()
    by = {t["currency"]: t for t in d["totals_by_currency"]}
    assert by["INR"]["total_annual"] == "6660000.00"       # original currency, untouched
    assert by["EUR"]["total_annual"] == "56400.00"          # 4700 x 12
    assert by["USD"]["total_annual"] == "250000.00"         # terminated excluded
    assert by["INR"]["total_annual_reporting"] == "80000.00"
    assert by["EUR"]["total_annual_reporting"] == "61304.35"
    assert d["total_compensation_reporting"] == "391304.35"


def test_overall_average_and_median_in_reporting_currency(client, auth, population):
    # USD annual: 80,000 | 200,000 | 61,304.35 | 50,000
    d = client.get(f"{A}/dashboard", params={"currency": "USD"}, headers=auth).json()["overall"]
    assert d["count"] == 4
    assert d["average"] == "97826.09"
    assert d["median"] == "70652.17"   # mean of 61,304.35 and 80,000
    assert d["minimum"] == "50000.00" and d["maximum"] == "200000.00"


def test_changing_reporting_currency_rescales_values_and_reports_rate_date(client, auth, population):
    d = client.get(f"{A}/dashboard", params={"currency": "INR"}, headers=auth).json()
    usd = client.get(f"{A}/dashboard", params={"currency": "USD"}, headers=auth).json()
    assert abs(Decimal(d["overall"]["average"]) - Decimal(usd["overall"]["average"]) * Decimal("83.25")) < 1
    assert d["rate_info"]["reporting_currency"] == "INR"
    assert d["rate_info"]["as_of"] == "2026-01-01"
    assert {r["from_currency"] for r in d["rate_info"]["rates"]} == {"USD", "EUR"}


def test_department_stats_highest_lowest_and_median(client, auth, population):
    g = client.get(f"{A}/departments", params={"currency": "USD"}, headers=auth).json()["groups"]
    eng = next(x for x in g if x["label"] == "Engineering")
    assert (eng["count"], eng["minimum"], eng["maximum"], eng["median"], eng["average"]) == (
        3, "61304.35", "200000.00", "80000.00", "113768.12"
    )
    sales = next(x for x in g if x["label"] == "Sales")
    assert sales["count"] == 1 and sales["minimum"] == sales["maximum"] == "50000.00"


def test_country_stats(client, auth, population):
    g = {x["label"]: x for x in client.get(f"{A}/countries", params={"currency": "USD"}, headers=auth).json()["groups"]}
    assert set(g) == {"India", "United States", "Germany"}  # Canada has no pay record
    assert g["Germany"]["average"] == "61304.35"


def test_salary_bands_count_everyone_once(client, auth, population):
    r = client.get(f"{A}/distribution", params={"currency": "USD"}, headers=auth).json()
    counts = {b["label"]: b["count"] for b in r["bands"]}
    assert sum(counts.values()) == 4
    assert counts["30K–60K"] == 1      # 50,000
    assert counts["60K–90K"] == 2      # 61,304.35 and 80,000
    assert counts["160K–220K"] == 1    # 200,000


def test_salary_band_edges_scale_with_reporting_currency(client, auth, population):
    r = client.get(f"{A}/distribution", params={"currency": "INR"}, headers=auth).json()
    assert Decimal(r["bands"][1]["lower"]) == Decimal("2500000")   # 30K USD -> 2,497,500 -> 2 s.f.
    assert r["bands"][1]["label"] == "2.5M–5M"
    assert sum(b["count"] for b in r["bands"]) == 4


def test_trends_group_changes_by_month(client, auth, make_employee, db):
    e = make_employee(joining_date="2023-01-10")
    cid = e["compensation"]["id"]
    for d, pct in (("2023-06-01", "10"), ("2023-06-20", "20"), ("2023-08-01", "5")):
        client.post(
            f"/api/v1/compensation/{cid}/increment",
            json={"type": "percentage", "value": pct, "effective_date": d, "reason": "Review"},
            headers=auth,
        )
    pts = client.get(f"{A}/trends", params={"currency": "INR"}, headers=auth).json()["points"]
    assert [(p["month"], p["changes"]) for p in pts] == [("2023-06", 2), ("2023-08", 1)]
    assert pts[0]["average_increment_percentage"] == "15.00"


def test_recent_changes_exclude_initial_records(client, auth, make_employee):
    e = make_employee()
    client.post(
        f"/api/v1/compensation/{e['compensation']['id']}/increment",
        json={"type": "fixed", "value": "1000", "effective_date": date.today().isoformat(), "reason": "Spot bonus"},
        headers=auth,
    )
    d = client.get(f"{A}/dashboard", headers=auth).json()
    assert [c["change_type"] for c in d["recent_changes"]] == ["fixed_increment"]


def test_missing_exchange_rate_gives_actionable_error(client, auth, population, db):
    from sqlalchemy import text

    db.execute(text("DELETE FROM exchange_rates"))
    db.commit()
    r = client.get(f"{A}/dashboard", headers=auth)
    assert r.status_code == 422 and "exchange rate" in r.json()["error"]["message"].lower()
