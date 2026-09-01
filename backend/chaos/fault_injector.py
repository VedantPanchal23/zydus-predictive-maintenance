"""
Chaos & Fault Injection Resilience Engine
==========================================
Simulates severe mechanical, thermal, and electrical fault modes to prove
automated detection, isolation, alert escalation, and GxP audit compliance.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from core.db_pool import get_db_cursor
from core.audit_logger import log_audit_event
from ml.inference import InferenceService
from incident.alert_engine import evaluate_alerts_for_equipment

logger = logging.getLogger("fault-injector")


def inject_fault(
    equipment_id: str,
    fault_type: str,
    user_id: str = "CHAOS_ENGINEER",
) -> Dict[str, Any]:
    """
    Injects synthetic fault telemetry into TimescaleDB and triggers ML re-evaluation.
    Supported fault types:
    - SEIZED_ROTOR (High Current + 0 RPM)
    - COOLING_FAILURE (High Temp + Low Flow)
    - BEARING_DEGRADATION (Severe Vibration Spike)
    """
    now = datetime.now(timezone.utc)
    readings = []

    if fault_type == "SEIZED_ROTOR":
        readings = [
            (equipment_id, "current_draw_a", 88.5, "A", now),
            (equipment_id, "motor_rpm", 0.0, "RPM", now),
            (equipment_id, "temperature_c", 68.0, "C", now),
            (equipment_id, "vibration_hz", 35.0, "Hz", now),
        ]
    elif fault_type == "COOLING_FAILURE":
        readings = [
            (equipment_id, "temperature_c", 98.5, "C", now),
            (equipment_id, "flow_rate_lpm", 2.1, "L/min", now),
            (equipment_id, "pressure_bar", 6.8, "bar", now),
            (equipment_id, "vibration_hz", 28.0, "Hz", now),
        ]
    elif fault_type == "BEARING_DEGRADATION":
        readings = [
            (equipment_id, "vibration_hz", 78.4, "Hz", now),
            (equipment_id, "temperature_c", 62.0, "C", now),
            (equipment_id, "current_draw_a", 48.0, "A", now),
        ]
    else:
        raise ValueError(f"Unknown fault type: '{fault_type}'")

    from domain.equipment import resolve_equipment_id
    eq_int = resolve_equipment_id(equipment_id)
    with get_db_cursor() as cur:
        for eq, s_name, val, unit, ts in readings:
            cur.execute(
                """
                INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, timestamp)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (eq_int, s_name, val, unit, ts),
            )

    log_audit_event(
        user_id=user_id,
        user_role="CHAOS_ENGINEER",
        action="INJECT_CHAOS_FAULT",
        entity_type="EQUIPMENT",
        entity_id=equipment_id,
        after_state={"fault_type": fault_type, "readings_count": len(readings)},
        reason_for_change=f"Automated resilience test injecting {fault_type}",
    )

    # Trigger instant ML prediction and alert check
    svc = InferenceService()
    pred = svc.predict(equipment_id)
    alert = evaluate_alerts_for_equipment(equipment_id)

    return {
        "equipment_id": equipment_id,
        "fault_type": fault_type,
        "injected_readings": len(readings),
        "prediction_result": pred,
        "alert_triggered": alert,
    }
