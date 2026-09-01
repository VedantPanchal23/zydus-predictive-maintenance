import pytest
from ml_service.alert_engine import (
    build_alert_classification,
    is_prediction_stale,
)
from datetime import datetime, timedelta, timezone

def test_warning_alert_classification():
    """Moderate failure probability triggers WARNING."""
    pred = {
        "failure_probability": 0.55,
        "anomaly_score": 0.40,
        "days_to_failure": 20.0,
    }
    classification = build_alert_classification(pred)
    assert classification is not None
    assert classification["severity"] == "WARNING"
    assert classification["create_work_order"] is False
    assert classification["cooldown_hours"] == 2

def test_critical_alert_classification():
    """High failure probability or low RUL triggers CRITICAL."""
    pred = {
        "failure_probability": 0.85,
        "anomaly_score": 0.92,
        "days_to_failure": 1.5,
    }
    classification = build_alert_classification(pred)
    assert classification is not None
    assert classification["severity"] == "CRITICAL"
    assert classification["create_work_order"] is True
    assert classification["cooldown_hours"] == 6

def test_stale_prediction_filter():
    """Predictions older than 10 minutes must be recognized as stale."""
    stale_pred = {
        "predicted_at": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
        "failure_probability": 0.90,
    }
    assert is_prediction_stale(stale_pred) is True

    fresh_pred = {
        "predicted_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        "failure_probability": 0.90,
    }
    assert is_prediction_stale(fresh_pred) is False
