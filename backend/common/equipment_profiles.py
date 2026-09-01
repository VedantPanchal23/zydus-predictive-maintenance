"""Re-export canonical Equipment Profiles."""
from core.equipment_profiles import (
    resolve_sensor_profile,
    recommended_action_for_risk,
    SENSOR_PROFILE_ALIASES,
    PROFILE_ACTIONS,
    DEFAULT_ACTIONS,
)

__all__ = [
    "resolve_sensor_profile",
    "recommended_action_for_risk",
    "SENSOR_PROFILE_ALIASES",
    "PROFILE_ACTIONS",
    "DEFAULT_ACTIONS",
]
