"""
Domain Model: Maintenance Prescriptions & GxP SOP Dispatcher
============================================================
Maps equipment types, failure modes, and degradation patterns to exact
GxP Standard Operating Procedures (SOPs), cleanroom PPE, and tooling specs.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class MaintenancePrescription(BaseModel):
    sop_code: str
    sop_title: str
    action_summary: str
    required_tooling: List[str]
    cleanroom_ppe: List[str]
    lubricant_spec: Optional[str] = None
    estimated_downtime_hours: float
    dual_signoff_required: bool
    qa_release_required: bool


PRESCRIPTION_MATRIX: Dict[str, MaintenancePrescription] = {
    "Granulation": MaintenancePrescription(
        sop_code="SOP-MNT-GRAN-402",
        sop_title="Granulator & Tablet Press Mechanical Drive Overhaul",
        action_summary="Inspect main rotor bearings, verify impeller seal integrity, check hydraulic pressure relief valves, and grease drive gearbox.",
        required_tooling=["Calibrated Torque Wrench (20-150 Nm)", "Laser Alignment Kit", "Stroboscopic Tachometer", "Vibration Analyzer Probe"],
        cleanroom_ppe=["Class C Cleanroom Suit", "Nitrile Gloves (Double)", "HEPA Powered Air Respirator", "Anti-Static Safety Shoes"],
        lubricant_spec="Kluberfood NH1 94-301 (NSF H1 Food-Grade Synthetic Grease)",
        estimated_downtime_hours=3.5,
        dual_signoff_required=True,
        qa_release_required=True,
    ),
    "Sterile Injectables": MaintenancePrescription(
        sop_code="SOP-MNT-STER-701",
        sop_title="Aseptic Filling Line & Lyophilizer Refrigeration Servicing",
        action_summary="Isolate sterile barrier, inspect peristaltic pump ceramic pistons, check silicone oil circulation pump seals, and execute post-repair CIP/SIP.",
        required_tooling=["Sanitary Tri-Clamp Torque Fixture", "Helium Leak Detector (< 1e-7 mbar.L/s)", "Digital Manometer", "Sterile Nitrogen Purge Kit"],
        cleanroom_ppe=["Sterile Grade A Isolator Gauntlets", "Sterile Tyvek Overall with Integrated Hood", "Sterile Goggles", "Latex Sterile Gloves"],
        lubricant_spec="Fomblin Y-VAC 3 Fluorinated Inert Vacuum Fluid",
        estimated_downtime_hours=6.0,
        dual_signoff_required=True,
        qa_release_required=True,
    ),
    "Bioprocessing": MaintenancePrescription(
        sop_code="SOP-MNT-BIO-503",
        sop_title="Bioreactor Agitator Mechanical Seal & TFF Pump Overhaul",
        action_summary="Verify magnetic drive coupling alignment, replace peristaltic tubing cassette, calibrate pressure transducers, and test CIP spray ball coverage.",
        required_tooling=["Magnetic Flux Tester", "Sanitary Pressure Calibrator", "Borescope Camera", "TFF Differential Pressure Gauge"],
        cleanroom_ppe=["Class B Cleanroom Gown", "Safety Face Shield", "Neoprene Chemical Resistant Gloves", "Shoe Covers"],
        lubricant_spec="Silicone USP Class VI Fluid Dow Corning 360",
        estimated_downtime_hours=4.0,
        dual_signoff_required=True,
        qa_release_required=True,
    ),
    "Analytical Lab": MaintenancePrescription(
        sop_code="SOP-QC-LAB-204",
        sop_title="UPLC Pump Seal Replacement & Mass Spec Turbopump Servicing",
        action_summary="Replace dual sapphire plungers and high-pressure PTFE seals, inspect MS ion source capillary heater, and execute chromatographic system suitability test.",
        required_tooling=["HPLC Seal Extraction Tool Set", "Flowmeter Micro-Calibrator", "Torque Screwdriver (0.5-5 Nm)", "Lint-Free Optical Swabs"],
        cleanroom_ppe=["Laboratory Coat", "Safety Glasses", "Powder-Free Nitrile Gloves"],
        lubricant_spec="Inert Fluorosilicone Vacuum Grease",
        estimated_downtime_hours=2.0,
        dual_signoff_required=False,
        qa_release_required=False,
    ),
    "Hospital Oncology": MaintenancePrescription(
        sop_code="SOP-CLIN-RAD-901",
        sop_title="Linear Accelerator & Cryocooler Emergency Service Protocol",
        action_summary="Re-route active patient treatment schedule to backup suite, verify target cooling loop temperature, check helium compressor return pressure, and execute beam dosimetry QA.",
        required_tooling=["Calibrated Ionization Chamber Dosimeter", "Helium Pressure Charging Manifold", "RF Power Meter", "Thermal Imaging Camera"],
        cleanroom_ppe=["Radiation Dosimeter Badge", "Thermal Cryogenic Gloves", "Impact-Resistant Eye Protection", "Lead Apron (if beam test)"],
        lubricant_spec="Ultra-High Vacuum High-Purity Fluorolube",
        estimated_downtime_hours=4.5,
        dual_signoff_required=True,
        qa_release_required=True,
    ),
}


def get_prescription(category: str) -> MaintenancePrescription:
    """Returns the regulatory maintenance prescription for a given asset category."""
    return PRESCRIPTION_MATRIX.get(category, PRESCRIPTION_MATRIX["Granulation"])
