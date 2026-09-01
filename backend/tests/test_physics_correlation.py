import pytest
from ml.physics_correlation import analyze_physics_correlation

def test_nominal_physics_correlation():
    nominal_window = {
        "current_draw_a": [22.0, 23.5, 24.1, 22.8, 23.0],
        "motor_rpm": [1400.0, 1420.0, 1390.0, 1410.0, 1405.0],
        "temperature_c": [34.0, 34.5, 35.0, 34.8, 35.2],
    }
    res = analyze_physics_correlation(nominal_window, "GRAN-LINE-01")
    assert res.is_physically_anomalous is False
    assert len(res.detected_patterns) == 0

def test_detect_seized_rotor():
    # High current (75A) with 0 RPM
    seized_window = {
        "current_draw_a": [75.0, 78.0, 76.5, 79.0, 77.2],
        "motor_rpm": [0.0, 0.0, 0.0, 0.0, 0.0],
    }
    res = analyze_physics_correlation(seized_window, "GRAN-LINE-01")
    assert res.is_physically_anomalous is True
    assert any("SEIZED_ROTOR" in p for p in res.detected_patterns)
    assert res.decoupling_score >= 0.40

def test_detect_cooling_starvation():
    # High temp (85C) with 5 LPM flow
    starvation_window = {
        "temperature_c": [82.0, 85.0, 88.0, 86.5, 87.0],
        "flow_rate_lpm": [5.0, 4.2, 5.1, 4.8, 4.5],
    }
    res = analyze_physics_correlation(starvation_window, "FBD-DRYER-01")
    assert res.is_physically_anomalous is True
    assert any("COOLING_STARVATION" in p for p in res.detected_patterns)
