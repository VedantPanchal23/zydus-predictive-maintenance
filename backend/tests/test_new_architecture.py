import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def admin_headers(client):
    res = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_audit_chain_verification_endpoint(client, admin_headers):
    """Verify GET /api/audit-logs/verify returns valid status."""
    res = client.get("/api/audit-logs/verify", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "is_chain_valid" in data
    assert "status" in data
    assert data["status"] in ("SECURE_IMMUTABLE", "TAMPER_DETECTED")

def test_gxp_certificate_export_endpoint(client, admin_headers):
    """Verify GET /api/audit-logs/export/certificate returns valid certificate."""
    res = client.get("/api/audit-logs/export/certificate", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "certificate_id" in data
    assert "digital_signature_hash" in data
    assert data["standard"] == "US FDA 21 CFR Part 11 / EU Annex 11 / GAMP 5 Category 4"

def test_telemetry_ingest_and_dlq(client, admin_headers):
    """Verify POST /api/telemetry/ingest accepts valid and routes invalid to DLQ."""
    batch = {
        "readings": [
            {"equipment_id": "GRAN-LINE-01", "sensor_name": "vibration_hz", "value": 24.5, "unit": "Hz"},
            {"equipment_id": "GRAN-LINE-01", "sensor_name": "vibration_hz", "value": 999.0, "unit": "Hz"},
        ]
    }
    res = client.post("/api/telemetry/ingest", json=batch, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 1
    assert data["dlq_count"] == 1

def test_dlq_inspection_endpoint(client, admin_headers):
    """Verify GET /api/telemetry/dlq returns DLQ records."""
    res = client.get("/api/telemetry/dlq", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "dlq_records" in data
    assert "count" in data

def test_prometheus_metrics_endpoint(client):
    """Verify GET /metrics returns Prometheus format."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "pdm_telemetry_ingest_total" in res.text
    assert "pdm_inference_total" in res.text

def test_kubernetes_probes(client):
    """Verify /health, /health/live, /health/ready."""
    res1 = client.get("/health")
    assert res1.status_code == 200
    res2 = client.get("/health/live")
    assert res2.status_code == 200
    assert res2.json()["status"] == "alive"
