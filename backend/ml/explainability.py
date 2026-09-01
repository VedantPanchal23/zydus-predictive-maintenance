"""
Machine Learning Explainability & Feature Attribution Engine
============================================================
Calculates real-time per-sensor contribution to risk scores and anomaly residuals,
providing actionable root-cause diagnostics for maintenance engineers.
"""

from __future__ import annotations

from typing import Dict, Any, List
import numpy as np
from domain.equipment import get_equipment_profile


class SensorContribution:
    def __init__(
        self,
        sensor_name: str,
        impact_percentage: float,
        current_value: float,
        nominal_range: str,
        unit: str,
        severity_status: str,
    ):
        self.sensor_name = sensor_name
        self.impact_percentage = impact_percentage
        self.current_value = current_value
        self.nominal_range = nominal_range
        self.unit = unit
        self.severity_status = severity_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_name": self.sensor_name,
            "impact_percentage": round(self.impact_percentage, 1),
            "current_value": round(self.current_value, 2),
            "nominal_range": self.nominal_range,
            "unit": self.unit,
            "severity_status": self.severity_status,
        }


def compute_feature_attribution(
    equipment_id: str,
    latest_sensor_values: Dict[str, float],
    anomaly_score: float,
    failure_probability: float,
) -> List[Dict[str, Any]]:
    """
    Computes normalized residual contributions for each active sensor channel.
    """
    profile = get_equipment_profile(equipment_id)
    residuals: Dict[str, float] = {}
    details: Dict[str, Dict[str, Any]] = {}

    for sensor, val in latest_sensor_values.items():
        spec = profile.sensors.get(sensor) if profile else None
        if spec:
            nom_mid = (spec.nominal_low + spec.nominal_high) / 2.0
            nom_span = (spec.nominal_high - spec.nominal_low) / 2.0 + 1e-5
            diff = abs(val - nom_mid)
            residual = max(0.0, (diff - nom_span) / nom_span)
            
            # Severity classification
            if val >= spec.critical_high:
                status = "CRITICAL"
                residual *= 2.0
            elif val >= spec.warning_high:
                status = "WARNING"
                residual *= 1.5
            elif val < spec.nominal_low:
                status = "LOW_ANOMALOUS"
            else:
                status = "NOMINAL"

            residuals[sensor] = residual
            details[sensor] = {
                "val": val,
                "range": f"{spec.nominal_low} - {spec.nominal_high}",
                "unit": spec.unit,
                "status": status,
            }
        else:
            residuals[sensor] = 0.1
            details[sensor] = {
                "val": val,
                "range": "N/A",
                "unit": "",
                "status": "NOMINAL",
            }

    total_res = sum(residuals.values())
    if total_res <= 1e-6:
        # Uniform distribution when nominal
        uniform_pct = round(100.0 / max(1, len(latest_sensor_values)), 1)
        return [
            SensorContribution(
                sensor_name=s,
                impact_percentage=uniform_pct,
                current_value=details[s]["val"],
                nominal_range=details[s]["range"],
                unit=details[s]["unit"],
                severity_status=details[s]["status"],
            ).to_dict()
            for s in latest_sensor_values.keys()
        ]

    contributions = []
    for s, res in residuals.items():
        pct = (res / total_res) * 100.0
        contributions.append(
            SensorContribution(
                sensor_name=s,
                impact_percentage=pct,
                current_value=details[s]["val"],
                nominal_range=details[s]["range"],
                unit=details[s]["unit"],
                severity_status=details[s]["status"],
            )
        )

    # Sort descending by impact percentage
    contributions.sort(key=lambda c: c.impact_percentage, reverse=True)
    return [c.to_dict() for c in contributions]
