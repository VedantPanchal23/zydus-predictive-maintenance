import pytest
import httpx
import time

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="module")
def api_client():
    return httpx.Client(base_url=BASE_URL)

@pytest.fixture(scope="module")
def auth_token(api_client):
    """Logs in and retrieves a dynamic JWT token explicitly parsing the DB."""
    response = api_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200, "Seed user login failed on local DB."
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

def test_health(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "zydus-backend"}

def test_login_success(api_client):
    res = api_client.post("/auth/login", data={"username": "engineer1", "password": "eng123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "engineer"

def test_login_fail(api_client):
    res = api_client.post("/auth/login", data={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["detail"]["error"] is True

def test_no_auth(api_client):
    res = api_client.get("/api/equipment")
    assert res.status_code == 401

def test_get_equipment(api_client, auth_headers):
    res = api_client.get("/api/equipment", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 20
    # Dynamic check: ensure specific fields exist
    for eq in data:
        assert "id" in eq
        assert "current_health" in eq
        assert eq["current_health"] in ["healthy", "warning", "critical"]

def test_get_equipment_detail(api_client, auth_headers):
    # Fetch list to dynamically get an ID instead of hardcoding 1, although ID 1 is seeded.
    eqs = api_client.get("/api/equipment", headers=auth_headers).json()
    first_id = eqs[0]["id"]
    
    res = api_client.get(f"/api/equipment/{first_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == first_id
    assert "latest_prediction" in data

def test_get_sensors(api_client, auth_headers):
    res = api_client.get("/api/equipment/1/sensors", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    # The structure must group by sensor name dynamically from the DB telemetry
    assert len(data.keys()) > 0

def test_get_prediction(api_client, auth_headers):
    res = api_client.get("/api/equipment/1/prediction", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    # It might return a message if simulation just started, or full prediction.
    if "failure_probability" in data:
        assert 0.0 <= data["failure_probability"] <= 1.0

def test_get_alerts(api_client, auth_headers):
    res = api_client.get("/api/alerts?severity=ALL&status=ALL", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

def test_get_workorders(api_client, auth_headers):
    res = api_client.get("/api/workorders", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_dashboard_summary(api_client, auth_headers):
    res = api_client.get("/api/dashboard/summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    keys = ["total_equipment", "healthy_count", "warning_count", "critical_count", 
            "open_alerts", "critical_alerts", "open_workorders", "avg_health_score"]
    for k in keys:
        assert k in data

def test_acknowledge_alert(api_client, auth_headers):
    # Dynamically find an unacknowledged alert to test
    alerts_res = api_client.get("/api/alerts?status=open&limit=1", headers=auth_headers)
    data = alerts_res.json()
    
    if data["items"]:
        target_id = data["items"][0]["id"]
        res = api_client.patch(f"/api/alerts/{target_id}/acknowledge", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["acknowledged_at"] is not None
    else:
        pytest.skip("No unacknowledged alerts found in live DB to test logic.")

def test_complete_workorder(api_client, auth_headers):
    # Dynamically find an open work order
    wo_res = api_client.get("/api/workorders?status=open", headers=auth_headers)
    data = wo_res.json()
    
    if data:
        target_id = data[0]["id"]
        res = api_client.patch(f"/api/workorders/{target_id}/complete", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == 'completed'
        assert res.json()["completed_at"] is not None
    else:
        pytest.skip("No open work orders found in live DB to test logic.")
