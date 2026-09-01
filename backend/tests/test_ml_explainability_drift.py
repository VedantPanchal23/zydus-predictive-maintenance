import pytest
import numpy as np
from ml.explainability import compute_feature_attribution
from ml.drift_monitor import calculate_psi, evaluate_sensor_drift

def test_feature_attribution_ranking():
    """Verify that anomalous sensor gets highest attribution percentage."""
    values = {
        "vibration_hz": 68.0,   # Critical high (nominal 10-28)
        "temperature_c": 32.0,  # Nominal (20-42)
        "pressure_bar": 2.0,    # Nominal (1.0-2.5)
        "current_draw_a": 25.0, # Nominal (15-35)
        "motor_rpm": 1400.0,    # Nominal (800-1500)
    }
    attribution = compute_feature_attribution("GRAN-LINE-01", values, 0.85, 0.78)
    assert len(attribution) == 5
    top = attribution[0]
    assert top["sensor_name"] == "vibration_hz"
    assert top["impact_percentage"] > 40.0
    assert top["severity_status"] == "CRITICAL"

def test_psi_identical_distributions():
    """Identical distributions must have near-zero PSI."""
    arr = np.random.normal(50.0, 10.0, 100)
    psi = calculate_psi(arr, arr)
    assert psi < 0.05

def test_psi_drift_detection():
    """Drifted distribution must produce high PSI (> 0.25)."""
    baseline = np.random.normal(20.0, 3.0, 100)
    shifted = np.random.normal(45.0, 8.0, 100)  # Significant mean shift
    psi = calculate_psi(baseline, shifted)
    assert psi > 0.25
