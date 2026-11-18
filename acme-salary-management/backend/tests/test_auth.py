import jwt
import pytest

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from tests.conftest import TEST_PASSWORD


def test_password_hashing_is_salted_and_verifiable():
    a, b = hash_password("secret-pass"), hash_password("secret-pass")
    assert a != b and a != "secret-pass"
    assert verify_password("secret-pass", a) and not verify_password("wrong", a)


def test_login_returns_token_that_authenticates(client, ref):
    r = client.post("/api/v1/auth/login", json={"email": "HR@acme-demo.com", "password": TEST_PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "hr@acme-demo.com"
    assert "password" not in r.text


@pytest.mark.parametrize(
    "email,password", [("hr@acme-demo.com", "wrong"), ("nobody@acme-demo.com", TEST_PASSWORD)]
)
def test_bad_credentials_are_indistinguishable(client, ref, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/employees", "/api/v1/compensation", "/api/v1/analytics/dashboard",
     "/api/v1/exchange-rates", "/api/v1/lookups", "/api/v1/employees/1/salary-history"],
)
def test_endpoints_require_authentication(client, ref, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_write_endpoints_require_authentication(client, ref):
    assert client.post("/api/v1/employees", json={}).status_code == 401
    assert client.post("/api/v1/exchange-rates", json={}).status_code == 401


def test_expired_or_forged_tokens_rejected(client, user):
    secret = get_settings().jwt_secret
    expired = jwt.encode({"sub": str(user.id), "exp": 1}, secret, algorithm="HS256")
    forged = jwt.encode({"sub": str(user.id), "exp": 9999999999}, "another-secret-another-secret", algorithm="HS256")
    for tok in (expired, forged):
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_inactive_user_cannot_login(client, db, user):
    user.is_active = False
    db.commit()
    r = client.post("/api/v1/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert r.status_code == 401


def test_health_is_public_and_deep_check_hits_db(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health", params={"deep": "true"}).json() == {"status": "ok"}


def test_cors_allows_configured_origin_only(client):
    ok = client.options(
        "/api/v1/employees",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/api/v1/employees",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers
