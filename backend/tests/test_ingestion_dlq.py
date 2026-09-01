import pytest
from domain.telemetry import RawSensorReading
from ingestion.validator import validate_sensor_reading

def test_valid_telemetry_reading():
    reading = RawSensorReading(
        equipment_id="GRAN-LINE-01",
        sensor_name="vibration_hz",
        value=24.5,
        unit="Hz",
    )
    is_valid, err = validate_sensor_reading(reading)
    assert is_valid is True
    assert err is None

def test_reject_nan_telemetry():
    reading = RawSensorReading(
        equipment_id="GRAN-LINE-01",
        sensor_name="vibration_hz",
        value=float("nan"),
    )
    is_valid, err = validate_sensor_reading(reading)
    assert is_valid is False
    assert "NaN" in err

def test_reject_out_of_bounds_sensor():
    # Max physical for vibration is 100 Hz. 999.0 must be rejected.
    reading = RawSensorReading(
        equipment_id="GRAN-LINE-01",
        sensor_name="vibration_hz",
        value=999.0,
    )
    is_valid, err = validate_sensor_reading(reading)
    assert is_valid is False
    assert "out of physical bounds" in err

def test_reject_unknown_equipment():
    reading = RawSensorReading(
        equipment_id="NON-EXISTENT-PUMP-99",
        sensor_name="vibration_hz",
        value=25.0,
    )
    is_valid, err = validate_sensor_reading(reading)
    assert is_valid is False
    assert "Unknown equipment ID" in err
