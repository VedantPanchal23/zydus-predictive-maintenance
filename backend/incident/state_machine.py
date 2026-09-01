"""
Incident State Machine with Hysteresis Anti-Flapping Filter
===========================================================
Prevents transient alarm storms by enforcing consecutive breach confirmation
before escalating states (NORMAL -> WATCH -> WARNING -> CRITICAL) and requiring
recovery confirmation before de-escalating.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple


class EquipmentStateMachine:
    def __init__(self, escalation_threshold: int = 2, recovery_threshold: int = 3):
        self.escalation_threshold = escalation_threshold
        self.recovery_threshold = recovery_threshold
        # equipment_id -> {"state": "NORMAL", "breach_count": 0, "healthy_count": 0}
        self._states: Dict[str, Dict[str, Any]] = {}

    def update_state(
        self,
        equipment_id: str,
        failure_probability: float,
        anomaly_score: float,
        days_to_failure: float,
    ) -> Tuple[str, bool]:
        """
        Updates the equipment incident state with hysteresis filtering.
        Returns:
            (current_state, state_changed_flag)
        """
        if equipment_id not in self._states:
            self._states[equipment_id] = {
                "state": "NORMAL",
                "breach_count": 0,
                "healthy_count": 0,
            }

        tracker = self._states[equipment_id]
        curr = tracker["state"]
        prev = curr

        # Determine if current sample indicates an anomalous condition
        is_critical_raw = failure_probability >= 0.80 or days_to_failure <= 3.0
        is_warning_raw = failure_probability >= 0.40 or days_to_failure <= 14.0 or anomaly_score >= 0.85

        if is_critical_raw:
            tracker["breach_count"] += 1
            tracker["healthy_count"] = 0
            if tracker["breach_count"] >= self.escalation_threshold:
                tracker["state"] = "CRITICAL"
        elif is_warning_raw:
            tracker["breach_count"] += 1
            tracker["healthy_count"] = 0
            if tracker["breach_count"] >= self.escalation_threshold:
                if curr != "CRITICAL":
                    tracker["state"] = "WARNING"
            else:
                if curr == "NORMAL":
                    tracker["state"] = "WATCH"
        else:
            # Nominal condition
            tracker["healthy_count"] += 1
            tracker["breach_count"] = 0
            if tracker["healthy_count"] >= self.recovery_threshold:
                tracker["state"] = "NORMAL"

        changed = tracker["state"] != prev
        return tracker["state"], changed


state_machine = EquipmentStateMachine()
