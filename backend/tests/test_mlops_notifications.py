import pytest
import httpx
from services.notification_service import (
    format_slack_card,
    format_teams_card,
    dispatch_alert_webhook,
    is_in_cooldown,
    mark_dispatched,
)

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

def test_slack_card_formatting():
    alert = {
        "equipment_id": "GRAN-LINE-01",
        "severity": "CRITICAL",
        "message": "Thermal runaway detected",
        "financial_loss_inr": 2500000,
        "sop_code": "SOP-MNT-GRAN-301",
    }
    card = format_slack_card(alert)
    assert "attachments" in card
    blocks = card["attachments"][0]["blocks"]
    assert len(blocks) >= 2
    assert "GRAN-LINE-01" in blocks[0]["text"]["text"]

def test_teams_card_formatting():
    alert = {
        "equipment_id": "LINAC-01",
        "severity": "WARNING",
        "message": "Beam current drift",
        "financial_loss_inr": 95000000,
    }
    card = format_teams_card(alert)
    assert card["type"] == "message"
    assert "LINAC-01" in card["attachments"][0]["content"]["body"][0]["text"]

def test_notification_cooldown_deduplication():
    eq = "TEST-COOLDOWN-EQ"
    assert not is_in_cooldown(eq, "CRITICAL")
    mark_dispatched(eq, "CRITICAL")
    assert is_in_cooldown(eq, "CRITICAL")

def test_api_get_ml_drift_status(api_client, admin_headers):
    response = api_client.get("/api/ml/drift-status?equipment_id=GRAN-LINE-01", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "drift_status" in data
    assert "champion_model_version" in data
    assert "max_psi" in data

def test_api_trigger_ml_retraining(api_client, admin_headers):
    response = api_client.post(
        "/api/ml/retrain",
        headers=admin_headers,
        json={"equipment_id": "GRAN-LINE-01", "force_promotion": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_code"] == "GRAN-LINE-01"
    assert data["action"] == "PROMOTE_ML_CHAMPION"
    assert data["promoted"] is True

def test_api_test_alert_webhook(api_client, admin_headers):
    response = api_client.post(
        "/api/alerts/test-webhook",
        headers=admin_headers,
        json={
            "equipment_id": "ASEPTIC-FILL-01",
            "severity": "CRITICAL",
            "message": "Aseptic seal pressure loss",
            "financial_loss_inr": 4500000,
            "force_dispatch": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dispatched"] is True
