from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models import AuditLog, Compensation, SalaryHistory
from app.services import compensation as service
from tests.factories import add_employee

COMP = "/api/v1/compensation"


# ---- pure calculation ------------------------------------------------------------------------
def test_percentage_increment_matches_spec_example():
    new, inc, pct = service.calculate_increment(Decimal("1500000"), "percentage", Decimal("10"))
    assert (new, inc, pct) == (Decimal("1650000.00"), Decimal("150000.00"), Decimal("10"))


def test_fixed_increment_derives_percentage():
    new, inc, pct = service.calculate_increment(Decimal("1500000"), "fixed", Decimal("75000"))
    assert new == Decimal("1575000.00") and inc == Decimal("75000.00") and pct == Decimal("5.0000")


def test_percentage_rounds_half_up_to_cents_without_float_error():
    # 0.1 + 0.2 style float traps: 3% of 33.33 = 0.9999 -> 1.00
    new, inc, _ = service.calculate_increment(Decimal("33.33"), "percentage", Decimal("3"))
    assert inc == Decimal("1.00") and new == Decimal("34.33")
    new, inc, _ = service.calculate_increment(Decimal("100.05"), "percentage", Decimal("10"))
    assert inc == Decimal("10.01")  # 10.005 rounds half up


# ---- API: increments -------------------------------------------------------------------------
def test_percentage_increment_updates_salary_and_writes_history(client, auth, make_employee, db, user):
    e = make_employee()
    comp_id = e["compensation"]["id"]
    r = client.post(
        f"{COMP}/{comp_id}/increment",
        json={"type": "percentage", "value": "10", "effective_date": "2024-04-01", "reason": "Annual review"},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["amount"] == "1650000.00"
    rows = db.query(SalaryHistory).filter_by(employee_id=e["id"]).order_by(SalaryHistory.id).all()
    assert [h.change_type for h in rows] == ["initial", "percentage_increment"]
    h = rows[1]
    assert (h.previous_amount, h.new_amount) == (Decimal("1500000.00"), Decimal("1650000.00"))
    assert h.increment_percentage == Decimal("10.0000") and h.increment_amount == Decimal("150000.00")
    assert (h.previous_currency, h.new_currency) == ("INR", "INR")
    assert h.reason == "Annual review" and h.changed_by == user.id and h.created_at is not None


def test_fixed_increment(client, auth, make_employee, db):
    e = make_employee()
    r = client.post(
        f"{COMP}/{e['compensation']['id']}/increment",
        json={"type": "fixed", "value": "50000", "effective_date": "2024-04-01", "reason": "Promotion"},
        headers=auth,
    )
    assert r.json()["amount"] == "1550000.00"
    h = db.query(SalaryHistory).filter_by(change_type="fixed_increment").one()
    assert h.increment_amount == Decimal("50000.00") and h.increment_percentage == Decimal("3.3333")


def test_increment_preview_does_not_persist(client, auth, make_employee, db):
    e = make_employee()
    r = client.post(
        f"{COMP}/{e['compensation']['id']}/increment/preview",
        json={"type": "percentage", "value": "10", "effective_date": "2024-04-01", "reason": "Preview"},
        headers=auth,
    )
    assert r.json()["new_amount"] == "1650000.00"
    assert db.query(SalaryHistory).count() == 1
    assert db.query(Compensation).one().amount == Decimal("1500000.00")


@pytest.mark.parametrize(
    "body",
    [
        {"type": "percentage", "value": "0"},
        {"type": "percentage", "value": "-5"},
        {"type": "percentage", "value": "5000"},
        {"type": "fixed", "value": "-100"},
        {"type": "bogus", "value": "5"},
        {"type": "fixed", "value": "5", "reason": "x"},
    ],
)
def test_increment_validation(client, auth, make_employee, body):
    e = make_employee()
    full = {"effective_date": "2024-04-01", "reason": "Because", **body}
    r = client.post(f"{COMP}/{e['compensation']['id']}/increment", json=full, headers=auth)
    assert r.status_code == 422


def test_effective_date_cannot_precede_current_effective_date(client, auth, make_employee):
    e = make_employee(joining_date="2022-01-10")
    r = client.post(
        f"{COMP}/{e['compensation']['id']}/increment",
        json={"type": "fixed", "value": "10", "effective_date": "2021-01-01", "reason": "Backdated"},
        headers=auth,
    )
    assert r.status_code == 422


def test_increment_missing_compensation_404(client, auth, ref):
    r = client.post(
        f"{COMP}/999/increment",
        json={"type": "fixed", "value": "10", "effective_date": "2024-01-01", "reason": "Nope"},
        headers=auth,
    )
    assert r.status_code == 404


def test_terminated_employee_pay_is_frozen(client, auth, make_employee):
    e = make_employee()
    client.patch(f"/api/v1/employees/{e['id']}", json={"status": "terminated"}, headers=auth)
    r = client.post(
        f"{COMP}/{e['compensation']['id']}/increment",
        json={"type": "fixed", "value": "10", "effective_date": "2024-01-01", "reason": "Too late"},
        headers=auth,
    )
    assert r.status_code == 409


# ---- API: set / currency / frequency ---------------------------------------------------------
def test_update_salary_records_before_and_after(client, auth, make_employee, db):
    e = make_employee()
    r = client.patch(
        f"{COMP}/{e['compensation']['id']}",
        json={"amount": "1800000", "effective_date": "2024-07-01", "reason": "Market correction"},
        headers=auth,
    )
    assert r.status_code == 200 and r.json()["amount"] == "1800000.00"
    h = db.query(SalaryHistory).filter_by(change_type="set").one()
    assert (h.previous_amount, h.new_amount) == (Decimal("1500000.00"), Decimal("1800000.00"))
    assert h.increment_percentage is None


def test_change_currency_and_frequency_keeps_both_sides_in_history(client, auth, make_employee, db):
    e = make_employee()
    r = client.patch(
        f"{COMP}/{e['compensation']['id']}",
        json={
            "amount": "7000", "currency": "EUR", "frequency": "monthly",
            "effective_date": "2024-07-01", "reason": "Relocation to Germany",
        },
        headers=auth,
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["currency"], body["frequency"], body["amount"]) == ("EUR", "monthly", "7000.00")
    h = db.query(SalaryHistory).filter_by(change_type="set").one()
    assert (h.previous_currency, h.new_currency) == ("INR", "EUR")
    assert (h.previous_frequency, h.new_frequency) == ("annual", "monthly")
    assert h.previous_amount == Decimal("1500000.00")


@pytest.mark.parametrize("override", [{"amount": "-1"}, {"currency": "GBP"}, {"frequency": "weekly"}, {"reason": ""}])
def test_update_validation(client, auth, make_employee, override):
    e = make_employee()
    body = {"amount": "1", "effective_date": "2024-07-01", "reason": "Valid reason", **override}
    assert client.patch(f"{COMP}/{e['compensation']['id']}", json=body, headers=auth).status_code == 422


def test_create_compensation_for_employee_without_one(client, auth, make_employee, db):
    e = make_employee(compensation=None)
    r = client.post(
        COMP,
        json={"employee_id": e["id"], "amount": "100000", "currency": "USD", "frequency": "annual",
              "effective_date": "2024-01-01", "reason": "Backfilled record"},
        headers=auth,
    )
    assert r.status_code == 201
    assert db.query(SalaryHistory).filter_by(employee_id=e["id"], change_type="initial").count() == 1


def test_cannot_create_second_compensation(client, auth, make_employee):
    e = make_employee()
    r = client.post(
        COMP,
        json={"employee_id": e["id"], "amount": "1", "currency": "USD", "frequency": "annual",
              "effective_date": "2024-01-01", "reason": "Duplicate"},
        headers=auth,
    )
    assert r.status_code == 409


def test_list_compensation_filters_and_paginates(client, auth, db, ids):
    for i in range(1, 6):
        add_employee(db, ids, i, currency="INR" if i < 4 else "USD")
    r = client.get(COMP, params={"currency": "USD"}, headers=auth)
    assert r.json()["total"] == 2
    r = client.get(COMP, params={"page_size": 2, "page": 3}, headers=auth)
    assert len(r.json()["items"]) == 1 and r.json()["pages"] == 3


# ---- transactions & immutability -------------------------------------------------------------
def test_failure_after_history_insert_rolls_back_compensation_update(
    client, auth, make_employee, db, monkeypatch
):
    """The compensation row and its history row are one transaction: if anything later in the
    unit of work fails, neither change is visible."""
    e = make_employee()
    cid = e["compensation"]["id"]

    def boom(*_a, **_k):
        raise RuntimeError("simulated failure after history insert")

    monkeypatch.setattr(service.audit, "record", boom)
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post(
            f"{COMP}/{cid}/increment",
            json={"type": "percentage", "value": "10", "effective_date": "2024-04-01", "reason": "Will fail"},
            headers=auth,
        )
    assert r.status_code == 500
    db.expire_all()
    assert db.get(Compensation, cid).amount == Decimal("1500000.00")
    assert db.query(SalaryHistory).filter_by(employee_id=e["id"]).count() == 1  # only 'initial'


def test_failed_increment_does_not_touch_history_or_audit(client, auth, make_employee, db):
    e = make_employee()
    before_audit = db.query(AuditLog).count()
    r = client.post(
        f"{COMP}/{e['compensation']['id']}/increment",
        json={"type": "fixed", "value": "5", "effective_date": "1999-01-01", "reason": "Invalid date"},
        headers=auth,
    )
    assert r.status_code == 422
    assert db.query(SalaryHistory).count() == 1
    assert db.query(AuditLog).count() == before_audit


def test_salary_history_rows_cannot_be_updated_or_deleted(make_employee, db):
    e = make_employee()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE salary_history SET new_amount = 1 WHERE employee_id = :i"), {"i": e["id"]})
    db.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("DELETE FROM salary_history WHERE employee_id = :i"), {"i": e["id"]})
    db.rollback()
    assert db.query(SalaryHistory).filter_by(employee_id=e["id"]).count() == 1


def test_database_rejects_negative_salary_and_unknown_currency(make_employee, db):
    e = make_employee()
    for sql in (
        "UPDATE compensation SET amount = -1 WHERE employee_id = :i",
        "UPDATE compensation SET currency = 'GBP' WHERE employee_id = :i",
        "UPDATE compensation SET frequency = 'weekly' WHERE employee_id = :i",
    ):
        with pytest.raises(DBAPIError):
            db.execute(text(sql), {"i": e["id"]})
        db.rollback()


# ---- history endpoint ------------------------------------------------------------------------
def test_salary_history_endpoint_is_chronological_and_names_the_hr_user(client, auth, make_employee):
    e = make_employee(joining_date="2022-01-10")
    cid = e["compensation"]["id"]
    for date_, pct in (("2023-04-01", "10"), ("2024-04-01", "5")):
        client.post(
            f"{COMP}/{cid}/increment",
            json={"type": "percentage", "value": pct, "effective_date": date_, "reason": "Annual review"},
            headers=auth,
        )
    asc = client.get(f"/api/v1/employees/{e['id']}/salary-history", headers=auth).json()
    assert [h["effective_date"] for h in asc] == ["2022-01-10", "2023-04-01", "2024-04-01"]
    assert asc[0]["change_type"] == "initial" and asc[0]["previous_amount"] is None
    assert asc[-1]["new_amount"] == "1732500.00"
    assert asc[1]["changed_by_name"] == "Hannah HR"
    desc = client.get(f"/api/v1/employees/{e['id']}/salary-history", params={"order": "desc"}, headers=auth).json()
    assert [h["id"] for h in desc] == [h["id"] for h in reversed(asc)]
