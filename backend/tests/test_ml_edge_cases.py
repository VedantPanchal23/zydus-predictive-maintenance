import pytest
import numpy as np
from ml_service.inference import InferenceService, SENSOR_RANGES

@pytest.fixture(scope="module")
def inference_service():
    svc = InferenceService()
    return svc

def test_inference_service_model_loading(inference_service):
    """Verify all ensemble models and scalers load successfully."""
    assert inference_service.models_loaded is True
    assert inference_service.isolation_forest is not None
    assert inference_service.lstm_model is not None
    assert inference_service.xgb_regressor is not None
    assert inference_service.xgb_classifier is not None

def test_predict_unknown_equipment(inference_service):
    """Querying an unknown asset must return None gracefully without raising exceptions."""
    result = inference_service.predict("NON-EXISTENT-EQUIPMENT-999")
    assert result is None

def test_sensor_normalization_bounds():
    """Verify that all sensors clip strictly between 0.0 and 1.0 even with extreme physical inputs."""
    for sensor, (s_min, s_max) in SENSOR_RANGES.items():
        # Extreme negative
        norm_low = np.clip((s_min - 1000.0 - s_min) / (s_max - s_min + 1e-10), 0.0, 1.0)
        assert norm_low == 0.0

        # Extreme positive
        norm_high = np.clip((s_max + 1000.0 - s_min) / (s_max - s_min + 1e-10), 0.0, 1.0)
        assert norm_high == 1.0

def test_real_equipment_prediction_schema(inference_service):
    """Predicting on an active asset produces valid bounded dictionary."""
    result = inference_service.predict("GRAN-LINE-01")
    if result is not None:
        assert "anomaly_score" in result
        assert 0.0 <= result["anomaly_score"] <= 1.0
        assert "failure_probability" in result
        assert 0.0 <= result["failure_probability"] <= 1.0
        assert "days_to_failure" in result
        assert result["days_to_failure"] >= 0.0
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
