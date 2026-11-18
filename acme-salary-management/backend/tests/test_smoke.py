def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get(client, auth, make_employee):
    e = make_employee()
    assert e["employee_code"].startswith("ACME-")
    assert e["compensation"]["amount"] == "1500000.00"
    r = client.get(f"/api/v1/employees/{e['id']}", headers=auth)
    assert r.status_code == 200
