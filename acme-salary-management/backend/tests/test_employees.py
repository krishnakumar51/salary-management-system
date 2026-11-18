import pytest

from app.models import AuditLog, Employee, SalaryHistory

API = "/api/v1/employees"


def test_create_employee_generates_unique_code_and_initial_history(client, auth, make_employee, db):
    a = make_employee()
    b = make_employee()
    assert a["employee_code"] != b["employee_code"]
    assert a["full_name"] == "Test1 Person1"
    history = db.query(SalaryHistory).filter_by(employee_id=a["id"]).all()
    assert len(history) == 1 and history[0].change_type == "initial"
    assert db.query(AuditLog).filter_by(action="employee.create").count() == 2


def test_create_employee_without_compensation_is_allowed(make_employee):
    e = make_employee(compensation=None)
    assert e["compensation"] is None


def test_get_employee_returns_profile_fields(client, auth, make_employee, ids, db):
    boss = make_employee()
    e = make_employee(manager_id=boss["id"], phone="+91 98765 43210")
    r = client.get(f"{API}/{e['id']}", headers=auth)
    body = r.json()
    assert r.status_code == 200
    assert body["manager"]["id"] == boss["id"]
    assert body["phone"] == "+91 98765 43210"
    assert body["country"]["code"] == "IN"
    assert body["department"]["name"] == "Engineering"
    assert body["compensation"]["currency"] == "INR"


def test_get_missing_employee_is_404_with_error_envelope(client, auth, ref):
    r = client.get(f"{API}/9999", headers=auth)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_duplicate_email_is_conflict_case_insensitive(client, auth, make_employee, ids):
    make_employee(email="dup@acme-demo.com")
    payload = {
        "first_name": "B", "last_name": "C", "email": "DUP@acme-demo.com",
        "country_id": ids["country"]["IN"], "department_id": ids["department"]["Sales"],
        "designation": "Account Executive", "joining_date": "2023-01-01",
    }
    r = client.post(API, json=payload, headers=auth)
    assert r.status_code == 409
    assert r.json()["error"]["details"][0]["field"] == "email"


def test_duplicate_employee_code_is_conflict(client, auth, make_employee, ids):
    make_employee(employee_code="ACME-777")
    r = client.post(
        API,
        json={
            "employee_code": "ACME-777", "first_name": "B", "last_name": "C",
            "email": "other@acme-demo.com", "country_id": ids["country"]["IN"],
            "department_id": ids["department"]["Sales"], "designation": "Account Executive",
            "joining_date": "2023-01-01",
        },
        headers=auth,
    )
    assert r.status_code == 409


@pytest.mark.parametrize(
    "override, field",
    [
        ({"email": "not-an-email"}, "email"),
        ({"first_name": "  "}, "first_name"),
        ({"phone": "abc"}, "phone"),
        ({"employment_type": "volunteer"}, "employment_type"),
        ({"joining_date": "1950-01-01"}, "joining_date"),
        ({"joining_date": "2999-01-01"}, "joining_date"),
        ({"compensation": {"amount": "-5", "currency": "INR", "frequency": "annual"}}, "compensation.amount"),
        ({"compensation": {"amount": "10", "currency": "JPY", "frequency": "annual"}}, "compensation.currency"),
        ({"compensation": {"amount": "10", "currency": "INR", "frequency": "weekly"}}, "compensation.frequency"),
        ({"compensation": {"amount": "10.123", "currency": "INR", "frequency": "annual"}}, "compensation.amount"),
    ],
)
def test_create_rejects_invalid_input(client, auth, ids, override, field):
    payload = {
        "first_name": "A", "last_name": "B", "email": "valid@acme-demo.com",
        "country_id": ids["country"]["IN"], "department_id": ids["department"]["Sales"],
        "designation": "Account Executive", "joining_date": "2023-01-01",
    }
    payload.update(override)
    r = client.post(API, json=payload, headers=auth)
    assert r.status_code == 422
    fields = [d["field"] for d in r.json()["error"]["details"]]
    assert field in fields


def test_create_rejects_unknown_country_and_manager(client, auth, ids):
    base = {
        "first_name": "A", "last_name": "B", "email": "x@acme-demo.com",
        "department_id": ids["department"]["Sales"], "designation": "Account Executive",
        "joining_date": "2023-01-01",
    }
    r = client.post(API, json={**base, "country_id": 9999}, headers=auth)
    assert r.status_code == 422
    r = client.post(API, json={**base, "country_id": ids["country"]["IN"], "manager_id": 9999}, headers=auth)
    assert r.status_code == 422


def test_failed_create_leaves_no_partial_rows(client, auth, ids, db):
    """A bad compensation must not leave an orphan employee (single transaction)."""
    payload = {
        "first_name": "A", "last_name": "B", "email": "partial@acme-demo.com",
        "country_id": ids["country"]["IN"], "department_id": ids["department"]["Sales"],
        "designation": "Account Executive", "joining_date": "2023-01-01",
        "compensation": {"amount": "-1", "currency": "INR", "frequency": "annual"},
    }
    assert client.post(API, json=payload, headers=auth).status_code == 422
    assert db.query(Employee).count() == 0


def test_patch_updates_only_supplied_fields(client, auth, make_employee, ids):
    e = make_employee()
    r = client.patch(
        f"{API}/{e['id']}",
        json={"designation": "Senior Engineer", "department_id": ids["department"]["Product"]},
        headers=auth,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["designation"] == "Senior Engineer"
    assert body["department"]["name"] == "Product"
    assert body["email"] == e["email"]


def test_patch_status_and_audit(client, auth, make_employee, db):
    e = make_employee()
    r = client.patch(f"{API}/{e['id']}", json={"status": "terminated"}, headers=auth)
    assert r.json()["status"] == "terminated"
    log = db.query(AuditLog).filter_by(action="employee.update").one()
    assert log.details["changed"]["status"]["to"] == "terminated"


def test_patch_cannot_clear_required_fields(client, auth, make_employee):
    e = make_employee()
    r = client.patch(f"{API}/{e['id']}", json={"email": None}, headers=auth)
    assert r.status_code == 422


def test_patch_duplicate_email_conflict(client, auth, make_employee):
    a = make_employee()
    b = make_employee()
    r = client.patch(f"{API}/{b['id']}", json={"email": a["email"]}, headers=auth)
    assert r.status_code == 409


def test_manager_cannot_be_self_or_create_cycle(client, auth, make_employee):
    a = make_employee()
    b = make_employee(manager_id=a["id"])
    assert client.patch(f"{API}/{a['id']}", json={"manager_id": a["id"]}, headers=auth).status_code == 422
    assert client.patch(f"{API}/{a['id']}", json={"manager_id": b["id"]}, headers=auth).status_code == 422


def test_patch_missing_employee_404(client, auth, ref):
    assert client.patch(f"{API}/12345", json={"designation": "Zed"}, headers=auth).status_code == 404
