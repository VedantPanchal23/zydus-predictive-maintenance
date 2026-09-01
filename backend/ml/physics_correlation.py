"""
Physics-Informed Sensor Cross-Correlation & Coupling Anomaly Engine
===================================================================
Analyzes multi-channel physical coupling (RPM vs Current vs Flow vs Temp)
to detect mechanical decoupling, seized rotors, and cooling blockages.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np


class PhysicsCorrelationResult:
    def __init__(
        self,
        is_physically_anomalous: bool,
        decoupling_score: float,
        detected_patterns: List[str],
        correlation_matrix: Dict[str, Dict[str, float]],
    ):
        self.is_physically_anomalous = is_physically_anomalous
        self.decoupling_score = decoupling_score
        self.detected_patterns = detected_patterns
        self.correlation_matrix = correlation_matrix

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_physically_anomalous": self.is_physically_anomalous,
            "decoupling_score": round(self.decoupling_score, 4),
            "detected_patterns": self.detected_patterns,
            "correlation_matrix": self.correlation_matrix,
        }


def analyze_physics_correlation(
    sensor_window: Dict[str, List[float]],
    equipment_id: str,
) -> PhysicsCorrelationResult:
    """
    Computes cross-correlation and physical rule violations across telemetry channels.
    """
    patterns: List[str] = []
    decoupling_penalty = 0.0

    sensors = list(sensor_window.keys())
    matrix: Dict[str, Dict[str, float]] = {}

    # 1. Compute Pearson correlation matrix across available channels
    for s1 in sensors:
        matrix[s1] = {}
        for s2 in sensors:
            arr1 = np.array(sensor_window[s1], dtype=np.float64)
            arr2 = np.array(sensor_window[s2], dtype=np.float64)
            min_len = min(len(arr1), len(arr2))
            if min_len >= 5:
                arr1_cut = arr1[-min_len:]
                arr2_cut = arr2[-min_len:]
                if np.std(arr1_cut) > 1e-6 and np.std(arr2_cut) > 1e-6:
                    corr = float(np.corrcoef(arr1_cut, arr2_cut)[0, 1])
                    matrix[s1][s2] = round(corr, 3)
                else:
                    matrix[s1][s2] = 1.0 if s1 == s2 else 0.0
            else:
                matrix[s1][s2] = 1.0 if s1 == s2 else 0.0

    # 2. Physics Rule 1: High Current with Low/Zero RPM (Seized Rotor / Jammed Drive)
    if "current_draw_a" in sensor_window and "motor_rpm" in sensor_window:
        recent_current = np.mean(sensor_window["current_draw_a"][-5:])
        recent_rpm = np.mean(sensor_window["motor_rpm"][-5:])
        if recent_current > 50.0 and recent_rpm < 100.0:
            patterns.append("SEIZED_ROTOR_DETECTED: High current draw with near-zero rotational speed.")
            decoupling_penalty += 0.45

    # 3. Physics Rule 2: High Temp with Low Coolant Flow (Cooling Jacket Obstruction)
    if "temperature_c" in sensor_window and "flow_rate_lpm" in sensor_window:
        recent_temp = np.mean(sensor_window["temperature_c"][-5:])
        recent_flow = np.mean(sensor_window["flow_rate_lpm"][-5:])
        if recent_temp > 60.0 and recent_flow < 20.0:
            patterns.append("COOLING_STARVATION: Elevated operating temperature with suppressed coolant flow.")
            decoupling_penalty += 0.40

    # 4. Physics Rule 3: High Vibration with Normal/Low Load (Bearing Mechanical Spallation)
    if "vibration_hz" in sensor_window and "current_draw_a" in sensor_window:
        recent_vib = np.mean(sensor_window["vibration_hz"][-5:])
        recent_current = np.mean(sensor_window["current_draw_a"][-5:])
        if recent_vib > 45.0 and recent_current < 30.0:
            patterns.append("UNLOADED_VIBRATION_SPIKE: High harmonic vibration without electrical loading (Bearing Spall).")
            decoupling_penalty += 0.35

    is_anomalous = len(patterns) > 0 or decoupling_penalty >= 0.30
    return PhysicsCorrelationResult(
        is_physically_anomalous=is_anomalous,
        decoupling_score=min(1.0, decoupling_penalty),
        detected_patterns=patterns,
        correlation_matrix=matrix,
    )
