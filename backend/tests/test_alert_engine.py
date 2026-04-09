from datetime import datetime, timedelta, timezone

from ml_service.alert_engine import build_alert_classification, is_prediction_stale


def test_build_alert_classification_returns_critical_for_multiple_signals():
    classification = build_alert_classification(
        {
            "failure_probability": 0.92,
            "anomaly_score": 0.95,
            "days_to_failure": 1.5,
        }
    )

    assert classification is not None
    assert classification["severity"] == "CRITICAL"
    assert classification["create_work_order"] is True
    assert "Immediate inspection required." in classification["message"]


def test_build_alert_classification_returns_warning_for_moderate_risk():
    classification = build_alert_classification(
        {
            "failure_probability": 0.45,
            "anomaly_score": 0.30,
            "days_to_failure": 40,
        }
    )

    assert classification is not None
    assert classification["severity"] == "WARNING"
    assert classification["create_work_order"] is False
    assert "Monitor closely." in classification["message"]


def test_build_alert_classification_returns_none_for_nominal_prediction():
    classification = build_alert_classification(
        {
            "failure_probability": 0.10,
            "anomaly_score": 0.15,
            "days_to_failure": 90,
        }
    )

    assert classification is None


def test_prediction_is_marked_stale_when_older_than_threshold():
    prediction = {
        "predicted_at": (
            datetime.now(timezone.utc) - timedelta(minutes=30)
        ).isoformat()
    }

    assert is_prediction_stale(prediction) is True


def test_prediction_is_not_stale_when_recent():
    prediction = {
        "predicted_at": (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
    }

    assert is_prediction_stale(prediction) is False
