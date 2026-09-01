import pytest
import httpx
from datetime import datetime, timedelta, timezone
from jose import jwt

BASE_URL = "http://localhost:8000"
JWT_SECRET = "change-this-before-production"
JWT_ALGORITHM = "HS256"

@pytest.fixture(scope="module")
def api_client():
    return httpx.Client(base_url=BASE_URL)

def test_tampered_jwt_token(api_client):
    """Tampered token signature must immediately return 401."""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.invalidsignature123"
    res = api_client.get("/api/equipment", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401
    assert res.json()["detail"]["error"] is True

def test_expired_jwt_token(api_client):
    """Expired token must be rejected."""
    expired_payload = {
        "sub": "admin",
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    res = api_client.get("/api/equipment", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401

def test_malformed_auth_header(api_client):
    """Missing Bearer prefix or whitespace anomalies."""
    res1 = api_client.get("/api/equipment", headers={"Authorization": "Basic 12345"})
    assert res1.status_code == 401

    res2 = api_client.get("/api/equipment", headers={"Authorization": ""})
    assert res2.status_code == 401

def test_sql_injection_in_login_attempt(api_client):
    """SQL injection strings must be safely parameterized and rejected."""
    payloads = [
        ("admin' OR '1'='1", "password"),
        ("admin'--", "password"),
        ("admin'; DROP TABLE users;--", "password"),
    ]
    for user_inj, pass_inj in payloads:
        res = api_client.post("/auth/login", data={"username": user_inj, "password": pass_inj})
        assert res.status_code == 401

def test_create_user_rbac_enforcement(api_client):
    """Only admin can create users; engineers and viewers cannot."""
    # 1. Login as engineer
    eng_res = api_client.post("/auth/login", data={"username": "engineer1", "password": "eng123"})
    eng_token = eng_res.json()["access_token"]
    
    # 2. Attempt user creation as engineer -> must be 401
    res = api_client.post(
        "/auth/users",
        headers={"Authorization": f"Bearer {eng_token}"},
        json={"username": "hacker", "password": "pass", "role": "admin"},
    )
    assert res.status_code == 401
