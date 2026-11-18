"""Directory search, filters, sorting and pagination (all executed in SQL)."""

from datetime import date

import pytest

from tests.factories import add_employee

API = "/api/v1/employees"


@pytest.fixture
def directory(db, ids):
    """12 employees with deliberately varied attributes."""
    add_employee(db, ids, 1, first="Aarav", last="Sharma", country="IN", department="Engineering",
                 designation="Software Engineer", amount="1500000", currency="INR", joining=date(2020, 1, 5))
    add_employee(db, ids, 2, first="Anika", last="Verma", country="IN", department="Sales",
                 designation="Account Executive", amount="900000", currency="INR", joining=date(2022, 6, 1))
    add_employee(db, ids, 3, first="John", last="Smith", country="US", department="Engineering",
                 designation="Software Engineer", amount="120000", currency="USD", joining=date(2019, 2, 11))
    add_employee(db, ids, 4, first="Joan", last="Smithers", country="US", department="Finance",
                 designation="Financial Analyst", amount="90000", currency="USD", joining=date(2023, 9, 1),
                 status="on_leave")
    add_employee(db, ids, 5, first="Lena", last="Müller", country="DE", department="Engineering",
                 designation="Software Engineer", amount="6000", currency="EUR", frequency="monthly",
                 joining=date(2018, 4, 1))
    add_employee(db, ids, 6, first="Klaus", last="Weber", country="DE", department="Legal",
                 designation="Legal Counsel", amount="80000", currency="EUR", joining=date(2021, 1, 1),
                 status="terminated")
    add_employee(db, ids, 7, first="Priya", last="Nair", country="IN", department="Design",
                 designation="Product Designer", amount="40", currency="USD", frequency="hourly",
                 employment_type="contract", joining=date(2024, 2, 1))
    add_employee(db, ids, 8, first="Percent", last="100%_Match", country="CA", department="Product",
                 designation="Product Manager", amount="110000", currency="USD", joining=date(2022, 1, 1),
                 email="pct@acme-demo.com")
    for i in range(9, 13):
        add_employee(db, ids, i, first="Filler", last=f"Person{i:02d}", country="SG",
                     department="Operations", designation="Operations Analyst", amount="70000",
                     currency="USD", joining=date(2023, 1, i))


def names(r):
    return [e["full_name"] for e in r.json()["items"]]


def test_search_by_name_is_case_insensitive_partial(client, auth, directory):
    assert names(client.get(API, params={"q": "aARav"}, headers=auth)) == ["Aarav Sharma"]


def test_search_by_full_name_terms_across_first_and_last(client, auth, directory):
    r = client.get(API, params={"q": "john smith"}, headers=auth)
    assert names(r) == ["John Smith"]


def test_search_by_employee_id(client, auth, directory):
    r = client.get(API, params={"q": "ACME-00003"}, headers=auth)
    assert names(r) == ["John Smith"]


def test_search_by_email(client, auth, directory):
    r = client.get(API, params={"q": "emp5@acme"}, headers=auth)
    assert names(r) == ["Lena Müller"]


def test_search_treats_like_wildcards_literally(client, auth, directory):
    assert client.get(API, params={"q": "%"}, headers=auth).json()["total"] == 1
    assert client.get(API, params={"q": "_"}, headers=auth).json()["total"] == 1
    assert names(client.get(API, params={"q": "100%_"}, headers=auth)) == ["Percent 100%_Match"]


def test_filter_by_department_country_status_designation(client, auth, directory, ids):
    r = client.get(API, params={"department_id": ids["department"]["Engineering"]}, headers=auth)
    assert r.json()["total"] == 3
    r = client.get(API, params={"country_id": ids["country"]["US"]}, headers=auth)
    assert sorted(names(r)) == ["Joan Smithers", "John Smith"]
    r = client.get(API, params={"status": "terminated"}, headers=auth)
    assert names(r) == ["Klaus Weber"]
    r = client.get(API, params={"designation": "Software Engineer"}, headers=auth)
    assert r.json()["total"] == 3
    r = client.get(API, params={"employment_type": "contract"}, headers=auth)
    assert names(r) == ["Priya Nair"]


def test_filters_combine_with_and(client, auth, directory, ids):
    r = client.get(
        API,
        params={"country_id": ids["country"]["IN"], "department_id": ids["department"]["Engineering"]},
        headers=auth,
    )
    assert names(r) == ["Aarav Sharma"]


def test_salary_range_filter_converts_to_reporting_currency(client, auth, directory):
    # Annual USD equivalents (USD->INR 83.25, USD->EUR 0.92):
    #   Aarav 1.5M INR=18,018 | Anika 900k INR=10,811 | John 120,000 | Joan 90,000
    #   Lena 72,000 EUR/yr = 78,261 | Klaus 80,000 EUR=86,957 | Priya 40*2080=83,200
    #   Percent 110,000 | fillers 70,000
    r = client.get(API, params={"salary_min": 80000, "salary_max": 100000, "currency": "USD"}, headers=auth)
    assert sorted(names(r)) == ["Joan Smithers", "Klaus Weber", "Priya Nair"]
    # Same band expressed in INR must select the same people
    r_inr = client.get(
        API, params={"salary_min": 80000 * 83.25, "salary_max": 100000 * 83.25, "currency": "INR"}, headers=auth
    )
    assert sorted(names(r_inr)) == sorted(names(r))


def test_salary_filter_rejects_inverted_range(client, auth, directory):
    r = client.get(API, params={"salary_min": 10, "salary_max": 5}, headers=auth)
    assert r.status_code == 422


def test_sort_by_name_default_and_descending(client, auth, directory):
    asc = names(client.get(API, params={"page_size": 100}, headers=auth))
    assert asc[0] == "Percent 100%_Match"  # sorted by last name; digits sort first
    desc = names(client.get(API, params={"page_size": 100, "order": "desc"}, headers=auth))
    assert desc == list(reversed(asc))


def test_sort_by_joining_date(client, auth, directory):
    r = client.get(API, params={"sort": "joining_date", "order": "asc"}, headers=auth)
    dates = [e["joining_date"] for e in r.json()["items"]]
    assert dates == sorted(dates)
    assert r.json()["items"][0]["full_name"] == "Lena Müller"


def test_sort_by_salary_uses_converted_annual_amount(client, auth, directory):
    r = client.get(API, params={"sort": "salary", "order": "desc", "currency": "USD", "page_size": 3}, headers=auth)
    assert names(r) == ["John Smith", "Percent 100%_Match", "Joan Smithers"]
    low = client.get(API, params={"sort": "salary", "order": "asc", "currency": "USD", "page_size": 2}, headers=auth)
    assert names(low) == ["Anika Verma", "Aarav Sharma"]


def test_pagination_metadata_and_disjoint_pages(client, auth, directory):
    p1 = client.get(API, params={"page": 1, "page_size": 5}, headers=auth).json()
    p2 = client.get(API, params={"page": 2, "page_size": 5}, headers=auth).json()
    p3 = client.get(API, params={"page": 3, "page_size": 5}, headers=auth).json()
    assert (p1["total"], p1["pages"], len(p1["items"])) == (12, 3, 5)
    assert len(p2["items"]) == 5 and len(p3["items"]) == 2
    ids_seen = [e["id"] for p in (p1, p2, p3) for e in p["items"]]
    assert len(set(ids_seen)) == 12


def test_page_beyond_last_is_empty_not_error(client, auth, directory):
    r = client.get(API, params={"page": 99, "page_size": 10}, headers=auth)
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 12


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"status": "gone"}, {"sort": "bogus"}])
def test_invalid_query_parameters_rejected(client, auth, directory, params):
    assert client.get(API, params=params, headers=auth).status_code == 422


def test_listing_runs_constant_number_of_queries(client, auth, directory, db):
    """Guards against N+1: query count must not grow with page size."""
    from sqlalchemy import event

    from app.db.session import get_engine

    engine = get_engine()
    counts = []

    def run(size):
        n = {"q": 0}

        def _count(*_):
            n["q"] += 1

        event.listen(engine, "before_cursor_execute", _count)
        try:
            assert client.get(API, params={"page_size": size}, headers=auth).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", _count)
        return n["q"]

    counts = [run(2), run(12)]
    assert counts[0] == counts[1]


def test_employee_without_compensation_still_listed(client, auth, db, ids):
    add_employee(db, ids, 50, first="No", last="Pay", amount=None)
    r = client.get(API, params={"q": "No Pay"}, headers=auth)
    assert r.json()["items"][0]["compensation"] is None


def test_salary_range_is_inclusive_at_exact_converted_edges(client, auth, db, ids):
    """EUR 46,000 is exactly USD 50,000 at 0.92 EUR/USD; a rounded 1/0.92 factor used to land a hair
    below and silently drop the employee from a 'min 50,000' filter."""
    add_employee(db, ids, 1, first="Edge", last="Low", country="DE", amount="46000", currency="EUR")
    add_employee(db, ids, 2, first="Edge", last="High", country="DE", amount="82800", currency="EUR")  # USD 90,000
    add_employee(db, ids, 3, first="Edge", last="Out", country="DE", amount="45999.99", currency="EUR")
    r = client.get(API, params={"salary_min": 50000, "salary_max": 90000, "currency": "USD"}, headers=auth)
    assert sorted(names(r)) == ["Edge High", "Edge Low"]
