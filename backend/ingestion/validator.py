"""
Telemetry Ingestion Validator
=============================
Performs schema, physical boundary, and timestamp verification on raw sensor streams.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any
from domain.equipment import get_equipment_profile
from domain.telemetry import RawSensorReading


def validate_sensor_reading(reading: RawSensorReading) -> Tuple[bool, Optional[str]]:
    """
    Validates a raw sensor reading against physical engineering boundaries.
    Returns:
        (is_valid, error_reason)
    """
    # 1. NaN or Infinite check
    if math.isnan(reading.value) or math.isinf(reading.value):
        return False, f"Sensor value is NaN or Infinite: {reading.value}"

    # 2. Equipment existence check
    profile = get_equipment_profile(reading.equipment_id)
    if not profile:
        return False, f"Unknown equipment ID: '{reading.equipment_id}'"

    # 3. Sensor existence check
    sensor_spec = profile.sensors.get(reading.sensor_name)
    if not sensor_spec:
        # Check standard common sensors
        if reading.sensor_name not in ("vibration_hz", "temperature_c", "pressure_bar", "current_draw_a", "motor_rpm", "flow_rate_lpm", "pulse_count", "door_open_sec", "beam_current_ma", "optical_transmittance"):
            return False, f"Unknown sensor '{reading.sensor_name}' for equipment '{reading.equipment_id}'"

    # 4. Physical boundary check if sensor_spec exists
    if sensor_spec:
        # Allow slight 10% margin beyond physical range before hard rejection as sensor failure
        margin = (sensor_spec.max_physical - sensor_spec.min_physical) * 0.10
        min_allowed = sensor_spec.min_physical - margin
        max_allowed = sensor_spec.max_physical + margin
        if reading.value < min_allowed or reading.value > max_allowed:
            return False, f"Value {reading.value} out of physical bounds [{min_allowed:.1f}, {max_allowed:.1f}] for sensor '{reading.sensor_name}'"

    # 5. Timestamp future check (> 5 minutes in future is rejected as clock skew)
    now = datetime.now(timezone.utc)
    ts = reading.timestamp if reading.timestamp else now
    if ts > now + timedelta(minutes=5):
        return False, f"Future timestamp rejected: {ts.isoformat()}"

    return True, None
