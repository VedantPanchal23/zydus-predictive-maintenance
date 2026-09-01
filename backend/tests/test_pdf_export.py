import pytest
import httpx

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="module")
def api_client():
    return httpx.Client(base_url=BASE_URL)

@pytest.fixture(scope="module")
def admin_headers(api_client):
    res = api_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_export_audit_trail_pdf(api_client, admin_headers):
    response = api_client.get("/api/audit-logs/export/pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000

def test_export_equipment_report_pdf(api_client, admin_headers):
    response = api_client.get("/api/equipment/1/report/pdf", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000
