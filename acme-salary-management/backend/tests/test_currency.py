from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.services import currency as fx

D = Decimal


def snap(*rows):
    return {(b, t): (D(r), d) for b, t, r, d in rows}


JAN = date(2026, 1, 1)
JUN = date(2026, 6, 1)


def test_identity_has_rate_one_and_no_date():
    r = fx.resolve_rate({}, "USD", "USD")
    assert r.rate == 1 and r.effective_date is None


def test_direct_rate():
    r = fx.resolve_rate(snap(("USD", "INR", "83.25", JAN)), "USD", "INR")
    assert r.rate == D("83.25") and r.effective_date == JAN


def test_inverse_rate():
    r = fx.resolve_rate(snap(("USD", "EUR", "0.92", JAN)), "EUR", "USD")
    assert r.rate == D(1) / D("0.92")


def test_triangulates_through_usd_and_reports_oldest_date():
    s = snap(("USD", "INR", "80", JAN), ("USD", "EUR", "0.5", JUN))
    r = fx.resolve_rate(s, "INR", "EUR")
    assert r.rate == D("0.5") / D("80")
    assert r.effective_date == JAN


def test_missing_rate_returns_none_and_require_raises_helpfully():
    assert fx.resolve_rate({}, "INR", "EUR") is None
    with pytest.raises(AppError) as exc:
        fx.require_rate({}, "INR", "EUR")
    assert exc.value.status_code == 422 and "INR" in exc.value.message


def test_convert_quantizes_to_cents_half_up():
    assert fx.convert(D("100.00"), D("0.925")) == D("92.50")
    assert fx.convert(D("1.005"), D("1")) == D("1.01")


def test_conversion_has_no_float_drift():
    # 1,500,000 INR at 1/83.25 -> exactly rounded decimal, independent of float representation
    rate = D(1) / D("83.25")
    assert fx.convert(D("1500000"), rate) == D("18018.02")


def test_snapshot_uses_latest_rate_on_or_before_as_of(db, ref):
    from app.models import ExchangeRate

    db.add(ExchangeRate(base_currency="USD", target_currency="INR", rate=D("90"),
                        effective_date=date(2026, 6, 1), source="June update"))
    db.commit()
    assert fx.load_snapshot(db, date(2026, 3, 1))[("USD", "INR")][0] == D("83.25")
    assert fx.load_snapshot(db, date(2026, 7, 1))[("USD", "INR")][0] == D("90")


# ---- API -------------------------------------------------------------------------------------
def test_create_and_list_exchange_rate(client, auth, ref):
    r = client.post(
        "/api/v1/exchange-rates",
        json={"base_currency": "USD", "target_currency": "INR", "rate": "84.10",
              "effective_date": "2026-07-01", "source": "Treasury memo"},
        headers=auth,
    )
    assert r.status_code == 201
    rows = client.get("/api/v1/exchange-rates", headers=auth).json()
    assert rows[0]["effective_date"] == "2026-07-01" and rows[0]["rate"].startswith("84.1")


def test_duplicate_pair_and_date_conflicts(client, auth, ref):
    body = {"base_currency": "USD", "target_currency": "INR", "rate": "84",
            "effective_date": "2026-01-01", "source": "Duplicate"}
    assert client.post("/api/v1/exchange-rates", json=body, headers=auth).status_code == 409


@pytest.mark.parametrize(
    "override",
    [{"rate": "0"}, {"rate": "-1"}, {"target_currency": "USD"}, {"base_currency": "GBP"}, {"source": ""}],
)
def test_invalid_exchange_rates_rejected(client, auth, ref, override):
    body = {"base_currency": "USD", "target_currency": "INR", "rate": "84",
            "effective_date": "2026-08-01", "source": "Manual", **override}
    assert client.post("/api/v1/exchange-rates", json=body, headers=auth).status_code == 422


def test_convert_endpoint(client, auth, ref):
    r = client.get(
        "/api/v1/exchange-rates/convert",
        params={"amount": "100000", "from_currency": "USD", "to_currency": "INR"},
        headers=auth,
    )
    assert r.json()["converted"] == "8325000.00"
    r = client.get(
        "/api/v1/exchange-rates/convert",
        params={"amount": "8325000", "from_currency": "INR", "to_currency": "EUR"},
        headers=auth,
    )
    assert r.json()["converted"] == "92000.00"  # INR -> USD -> EUR


def test_conversion_does_not_modify_stored_salaries(client, auth, make_employee, db):
    from app.models import Compensation

    make_employee()
    client.get("/api/v1/analytics/dashboard", params={"currency": "EUR"}, headers=auth)
    c = db.query(Compensation).one()
    assert (c.amount, c.currency) == (D("1500000.00"), "INR")


def test_resolved_rate_keeps_an_exact_fraction():
    r = fx.resolve_rate(snap(("USD", "EUR", "0.92", JAN)), "EUR", "USD")
    assert (r.num, r.den) == (D(1), D("0.92"))
    t = fx.resolve_rate(snap(("USD", "INR", "80", JAN), ("USD", "EUR", "0.5", JUN)), "INR", "EUR")
    assert (t.num, t.den) == (D("0.5"), D("80"))
