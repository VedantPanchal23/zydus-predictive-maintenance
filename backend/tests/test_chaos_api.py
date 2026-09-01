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

@pytest.fixture(scope="module")
def viewer_headers(api_client):
    res = api_client.post("/auth/login", data={"username": "viewer1", "password": "view123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_chaos_inject_authorized(api_client, admin_headers):
    response = api_client.post(
        "/api/chaos/inject",
        headers=admin_headers,
        json={"equipment_id": "GRAN-LINE-01", "fault_type": "SEIZED_ROTOR"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_id"] == "GRAN-LINE-01"
    assert data["fault_type"] == "SEIZED_ROTOR"
    assert "prediction_result" in data
    assert data["prediction_result"]["failure_probability"] > 0

def test_chaos_inject_cooling_failure(api_client, admin_headers):
    response = api_client.post(
        "/api/chaos/inject",
        headers=admin_headers,
        json={"equipment_id": "VIAL-FILL-01", "fault_type": "COOLING_FAILURE"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fault_type"] == "COOLING_FAILURE"
    assert data["injected_readings"] > 0

def test_chaos_inject_forbidden_for_viewer(api_client, viewer_headers):
    response = api_client.post(
        "/api/chaos/inject",
        headers=viewer_headers,
        json={"equipment_id": "GRAN-LINE-01", "fault_type": "SEIZED_ROTOR"},
    )
    assert response.status_code in (401, 403)

def test_equipment_metadata_enrichment_inr(api_client, admin_headers):
    response = api_client.get("/api/equipment", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 20
    gran = next((e for e in data if e["equipment_id"] == "GRAN-LINE-01"), None)
    assert gran is not None
    assert gran["facility"] == "Oral Solid Dosage Block A"
    assert gran["batch_value_inr"] == 2500000
    assert "High Shear Mixer Granulator" in gran["name"]
