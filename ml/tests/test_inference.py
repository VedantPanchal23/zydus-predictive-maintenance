import pytest
import psycopg2
import os

from ml_service.alert_engine import build_alert_classification

# Bypass any `.env` loaded strings referring to the docker 'postgres' hostname.
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@127.0.0.1:5432/zydus_db",
)

@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg2.connect(DB_URL)
    yield conn
    conn.close()


def test_anomaly_score_range(db_conn):
    """Validates the output of IsolationForest/LSTM bounds."""
    cur = db_conn.cursor()
    cur.execute("SELECT anomaly_score FROM predictions ORDER BY predicted_at DESC LIMIT 25")
    scores = cur.fetchall()
    cur.close()

    if not scores:
        pytest.skip("No predictions found in DB yet.")

    for (score,) in scores:
        if score is not None:
            assert 0.0 <= score <= 1.0


def test_failure_probability_range(db_conn):
    """failure_probability MUST be between 0.0 and 1.0."""
    cur = db_conn.cursor()
    cur.execute("SELECT failure_probability FROM predictions LIMIT 10")
    probs = cur.fetchall()
    cur.close()

    if not probs:
        pytest.skip("No predictions mapped.")

    for (prob,) in probs:
        if prob is not None:
            assert 0.0 <= prob <= 1.0


def test_days_to_failure_positive(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT days_to_failure FROM predictions LIMIT 10")
    days = cur.fetchall()
    cur.close()

    if not days:
        pytest.skip("No ML output mapped.")

    for (d,) in days:
        if d is not None:
            assert d >= 0


def test_critical_alert_triggered():
    """
    Test explicitly whether the alert classifier escalates critical risk.
    """
    classification = build_alert_classification(
        {
            "anomaly_score": 0.95,
            "failure_probability": 0.85,
            "days_to_failure": 2.1,
        }
    )

    assert classification is not None
    assert classification["severity"] == "CRITICAL"
    assert classification["create_work_order"] is True

def test_normal_no_alert():
    """
    Given failure_probability = 0.20 (Healthy state), assert it doesn't trigger 
    alert classification erroneously.
    """
    classification = build_alert_classification(
        {
            "anomaly_score": 0.50,
            "failure_probability": 0.20,
            "days_to_failure": 100.0,
        }
    )

    assert classification is None
