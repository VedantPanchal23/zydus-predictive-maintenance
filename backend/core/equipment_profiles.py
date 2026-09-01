"""Shared equipment profile helpers for inference and risk guidance."""

from __future__ import annotations

SENSOR_PROFILE_ALIASES: dict[str, str] = {
    # Core profiles
    "manufacturing_line": "manufacturing_line",
    "cold_storage": "cold_storage",
    "lab_hplc": "lab_hplc",
    "infusion_pump": "infusion_pump",
    "radiation_unit": "radiation_unit",
    # Expanded manufacturing equipment families
    "granulation_line": "manufacturing_line",
    "tablet_press": "manufacturing_line",
    "blister_packer": "manufacturing_line",
    "capsule_filler": "manufacturing_line",
    "coating_machine": "manufacturing_line",
    "vial_washer": "manufacturing_line",
    "aseptic_filler": "manufacturing_line",
    "cip_skid": "manufacturing_line",
    # Expanded cold-chain equipment families
    "ultra_low_freezer": "cold_storage",
    "cold_room": "cold_storage",
    "chiller_loop": "cold_storage",
    "stability_chamber": "cold_storage",
    # Expanded lab analytics families
    "hplc_system": "lab_hplc",
    "lc_ms": "lab_hplc",
    "dissolution_tester": "lab_hplc",
    "toc_analyzer": "lab_hplc",
    # Expanded care delivery families
    "syringe_pump": "infusion_pump",
    # Expanded oncology imaging/radiation families
    "linear_accelerator": "radiation_unit",
    "ct_scanner": "radiation_unit",
}


PROFILE_ACTIONS: dict[str, dict[str, str]] = {
    "manufacturing_line": {
        "critical": "Stop the line, inspect bearings and motor load immediately, and dispatch a critical work order.",
        "high": "Reduce throughput, inspect vibration and pressure loops in the current shift, and stage spare parts.",
        "warning": "Plan lubrication and calibration in the next maintenance window and increase monitoring frequency.",
        "watch": "Continue operation with tighter observation and verify baseline drift on the next round.",
        "stable": "No immediate action needed. Keep preventive maintenance on schedule.",
        "unknown": "Awaiting prediction data. Verify telemetry from the line sensors.",
    },
    "cold_storage": {
        "critical": "Move temperature-sensitive material to backup storage and inspect compressor and door seal integrity now.",
        "high": "Check coolant pressure, compressor duty cycle, and humidity control before the next batch transfer.",
        "warning": "Inspect door usage, clean condenser surfaces, and monitor temperature excursions closely.",
        "watch": "Monitor cold-chain trends and validate sensor calibration in routine checks.",
        "stable": "No immediate action needed. Continue standard cold-chain verification.",
        "unknown": "Awaiting prediction data. Confirm cold-chain telemetry is streaming.",
    },
    "lab_hplc": {
        "critical": "Pause analysis queue, inspect column pressure and flow path, and execute emergency calibration.",
        "high": "Run performance qualification checks and verify solvent delivery stability in this shift.",
        "warning": "Schedule preventative calibration and inspect baseline noise or pressure drift.",
        "watch": "Review trend charts and keep routine lab QA checks active.",
        "stable": "No immediate action needed. Continue with planned lab maintenance.",
        "unknown": "Awaiting prediction data. Confirm analytical instrument sensors are online.",
    },
    "infusion_pump": {
        "critical": "Remove from service, perform occlusion and flow-validation checks, and replace worn drive components.",
        "high": "Run a controlled bench test and inspect battery and pressure response before patient use.",
        "warning": "Schedule maintenance inspection and verify alarm and battery behavior.",
        "watch": "Keep under enhanced observation with routine function checks.",
        "stable": "No immediate action needed. Continue periodic verification.",
        "unknown": "Awaiting prediction data. Verify pump telemetry and connectivity.",
    },
    "radiation_unit": {
        "critical": "Hold treatment queue, run safety interlock checks, and perform immediate dosimetry QA.",
        "high": "Reduce operating load, verify cooling loop and beam consistency, and schedule urgent engineering review.",
        "warning": "Perform focused QA checks and monitor beam and cooling metrics more frequently.",
        "watch": "Continue standard operation with increased trend monitoring.",
        "stable": "No immediate action needed. Keep standard radiation QA cadence.",
        "unknown": "Awaiting prediction data. Confirm dosimetry and cooling telemetry is available.",
    },
}


DEFAULT_ACTIONS = {
    "critical": "Immediate inspection required and a critical maintenance response should be initiated.",
    "high": "Urgent engineering review is recommended in the current shift.",
    "warning": "Schedule preventive maintenance and increase monitoring.",
    "watch": "Continue operation with closer observation.",
    "stable": "No immediate action needed.",
    "unknown": "Awaiting prediction data for this equipment.",
}


def resolve_sensor_profile(equipment_type: str | None) -> str:
    normalized = (equipment_type or "").strip().lower()
    if not normalized:
        return "manufacturing_line"
    return SENSOR_PROFILE_ALIASES.get(normalized, normalized)


def recommended_action_for_risk(equipment_type: str | None, risk_level: str) -> str:
    profile = resolve_sensor_profile(equipment_type)
    action_map = PROFILE_ACTIONS.get(profile, DEFAULT_ACTIONS)
    return action_map.get(risk_level, action_map["unknown"])
