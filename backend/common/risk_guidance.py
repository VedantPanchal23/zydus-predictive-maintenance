"""Risk classification helpers for equipment responses."""

from __future__ import annotations

from common.equipment_profiles import recommended_action_for_risk


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_equipment_risk(
    equipment_type: str | None,
    failure_probability,
    anomaly_score,
    days_to_failure,
) -> dict:
    fp_raw = _to_float(failure_probability)
    anomaly_raw = _to_float(anomaly_score)
    dtf_raw = _to_float(days_to_failure)

    if fp_raw is None and anomaly_raw is None and dtf_raw is None:
        level = "unknown"
        reason = "No prediction data available yet."
        return {
            "risk_level": level,
            "risk_reason": reason,
            "recommended_action": recommended_action_for_risk(equipment_type, level),
        }

    fp = fp_raw if fp_raw is not None else 0.0
    anomaly = anomaly_raw if anomaly_raw is not None else 0.0
    dtf = dtf_raw if dtf_raw is not None else 999.0

    if fp >= 0.80 or anomaly >= 0.90 or dtf <= 3:
        level = "critical"
    elif fp >= 0.65 or anomaly >= 0.80 or dtf <= 7:
        level = "high"
    elif fp >= 0.40 or anomaly >= 0.70 or dtf <= 14:
        level = "warning"
    elif fp >= 0.20 or anomaly >= 0.50 or dtf <= 30:
        level = "watch"
    else:
        level = "stable"

    factors = []
    if fp_raw is not None:
        factors.append(f"failure probability {fp:.2f}")
    if anomaly_raw is not None:
        factors.append(f"anomaly score {anomaly:.2f}")
    if dtf_raw is not None:
        factors.append(f"days to failure {dtf:.1f}")

    reason = ", ".join(factors) if factors else "Partial prediction signals detected."

    return {
        "risk_level": level,
        "risk_reason": reason,
        "recommended_action": recommended_action_for_risk(equipment_type, level),
    }
