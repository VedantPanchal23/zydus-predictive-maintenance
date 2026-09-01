"""
Domain Model: Pharma & Oncology Equipment Directory
===================================================
Comprehensive metadata, physical sensor profiles, and engineering specifications
for 20 critical pharmaceutical manufacturing and hospital oncology assets.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SensorThreshold(BaseModel):
    unit: str
    min_physical: float
    max_physical: float
    nominal_low: float
    nominal_high: float
    warning_high: float
    critical_high: float


class EquipmentProfile(BaseModel):
    equipment_id: str
    name: str
    category: str
    criticality: str  # HIGH, CRITICAL, LIFE_CRITICAL
    batch_value_usd: float
    facility: str
    sensors: Dict[str, SensorThreshold]
    description: str


EQUIPMENT_DIRECTORY: Dict[str, EquipmentProfile] = {
    # -- 1. Solid Dosage & Granulation Line ------------------
    "GRAN-LINE-01": EquipmentProfile(
        equipment_id="GRAN-LINE-01",
        name="High Shear Mixer Granulator 600L",
        category="Granulation",
        criticality="CRITICAL",
        batch_value_usd=120000.0,
        facility="Oral Solid Dosage Block A",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=10.0, nominal_high=28.0, warning_high=45.0, critical_high=65.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=20.0, nominal_high=42.0, warning_high=60.0, critical_high=80.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=1.0, nominal_high=2.5, warning_high=4.0, critical_high=6.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=15.0, nominal_high=35.0, warning_high=55.0, critical_high=75.0),
            "motor_rpm": SensorThreshold(unit="RPM", min_physical=0.0, max_physical=3000.0, nominal_low=800.0, nominal_high=1500.0, warning_high=1900.0, critical_high=2400.0),
        },
        description="High shear granulation mixer for cytotoxic oncology tablet formulations.",
    ),
    "FBD-DRYER-01": EquipmentProfile(
        equipment_id="FBD-DRYER-01",
        name="Fluid Bed Dryer FBD-300",
        category="Granulation",
        criticality="HIGH",
        batch_value_usd=85000.0,
        facility="Oral Solid Dosage Block A",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=5.0, nominal_high=20.0, warning_high=35.0, critical_high=55.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=40.0, nominal_high=75.0, warning_high=90.0, critical_high=105.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=0.2, nominal_high=0.8, warning_high=1.5, critical_high=2.5),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=10.0, nominal_high=25.0, warning_high=40.0, critical_high=60.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=150.0, nominal_high=350.0, warning_high=420.0, critical_high=480.0),
        },
        description="Fluidized bed drying chamber with HEPA filtered process air.",
    ),
    "TAB-PRESS-01": EquipmentProfile(
        equipment_id="TAB-PRESS-01",
        name="Rotary Tablet Press 45-Station",
        category="Granulation",
        criticality="CRITICAL",
        batch_value_usd=150000.0,
        facility="Oral Solid Dosage Block A",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=15.0, nominal_high=32.0, warning_high=50.0, critical_high=70.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=22.0, nominal_high=40.0, warning_high=58.0, critical_high=75.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=2.0, nominal_high=5.0, warning_high=7.0, critical_high=9.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=20.0, nominal_high=45.0, warning_high=65.0, critical_high=85.0),
            "motor_rpm": SensorThreshold(unit="RPM", min_physical=0.0, max_physical=3000.0, nominal_low=1200.0, nominal_high=2200.0, warning_high=2600.0, critical_high=2900.0),
        },
        description="High-speed rotary press with compression force monitoring.",
    ),
    "COATER-01": EquipmentProfile(
        equipment_id="COATER-01",
        name="Auto-Coater Perforated Pan 150kg",
        category="Granulation",
        criticality="HIGH",
        batch_value_usd=95000.0,
        facility="Oral Solid Dosage Block A",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=22.0, warning_high=38.0, critical_high=58.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=35.0, nominal_high=65.0, warning_high=80.0, critical_high=98.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=1.0, nominal_high=3.0, warning_high=4.5, critical_high=6.5),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=12.0, nominal_high=28.0, warning_high=42.0, critical_high=62.0),
            "motor_rpm": SensorThreshold(unit="RPM", min_physical=0.0, max_physical=3000.0, nominal_low=300.0, nominal_high=800.0, warning_high=1100.0, critical_high=1400.0),
        },
        description="Aqueous and solvent-based film coating system for oncology tablets.",
    ),

    # -- 2. Sterile Injectables & Lyophilization -------------
    "VIAL-FILL-01": EquipmentProfile(
        equipment_id="VIAL-FILL-01",
        name="Aseptic Vial Filling & Stoppering Line",
        category="Sterile Injectables",
        criticality="LIFE_CRITICAL",
        batch_value_usd=450000.0,
        facility="Sterile Injectable Complex B",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=5.0, nominal_high=18.0, warning_high=30.0, critical_high=48.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=18.0, nominal_high=26.0, warning_high=35.0, critical_high=50.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=0.1, nominal_high=0.5, warning_high=1.0, critical_high=2.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=20.0, warning_high=32.0, critical_high=48.0),
            "pulse_count": SensorThreshold(unit="count", min_physical=0.0, max_physical=100000.0, nominal_low=5000.0, nominal_high=40000.0, warning_high=60000.0, critical_high=85000.0),
        },
        description="Class A isolator vial filling machine for sterile oncology biologics.",
    ),
    "LYO-CHAMBER-01": EquipmentProfile(
        equipment_id="LYO-CHAMBER-01",
        name="Industrial Freeze Dryer Lyophilizer 50m2",
        category="Sterile Injectables",
        criticality="LIFE_CRITICAL",
        batch_value_usd=600000.0,
        facility="Sterile Injectable Complex B",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=24.0, warning_high=40.0, critical_high=60.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=-80.0, max_physical=80.0, nominal_low=-55.0, nominal_high=25.0, warning_high=45.0, critical_high=65.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=5.0, nominal_low=0.001, nominal_high=0.1, warning_high=0.5, critical_high=1.5),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=25.0, nominal_high=60.0, warning_high=80.0, critical_high=95.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=50.0, nominal_high=200.0, warning_high=280.0, critical_high=360.0),
        },
        description="Lyophilization chamber with silicone oil shelf cooling and dual refrigeration.",
    ),
    "AUTOCLAVE-01": EquipmentProfile(
        equipment_id="AUTOCLAVE-01",
        name="Porous Load Steam Sterilizer 2000L",
        category="Sterile Injectables",
        criticality="CRITICAL",
        batch_value_usd=110000.0,
        facility="Sterile Injectable Complex B",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=4.0, nominal_high=15.0, warning_high=28.0, critical_high=45.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=150.0, nominal_low=115.0, nominal_high=124.0, warning_high=132.0, critical_high=142.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=1.8, nominal_high=2.6, warning_high=3.2, critical_high=4.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=15.0, nominal_high=35.0, warning_high=50.0, critical_high=70.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=80.0, nominal_high=220.0, warning_high=300.0, critical_high=400.0),
        },
        description="High-pressure saturated steam terminal autoclave sterilizer.",
    ),
    "WFI-STILL-01": EquipmentProfile(
        equipment_id="WFI-STILL-01",
        name="Multiple Effect WFI Generation Still",
        category="Sterile Injectables",
        criticality="LIFE_CRITICAL",
        batch_value_usd=250000.0,
        facility="Sterile Injectable Complex B",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=6.0, nominal_high=20.0, warning_high=34.0, critical_high=52.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=180.0, nominal_low=120.0, nominal_high=160.0, warning_high=170.0, critical_high=180.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=3.0, nominal_high=5.5, warning_high=7.0, critical_high=8.5),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=20.0, nominal_high=45.0, warning_high=65.0, critical_high=85.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=100.0, nominal_high=300.0, warning_high=380.0, critical_high=460.0),
        },
        description="USP/EP compliant Water For Injection distillation generation unit.",
    ),

    # -- 3. Bioprocessing & Oncology Monoclonal Antibodies --
    "BIOREACTOR-01": EquipmentProfile(
        equipment_id="BIOREACTOR-01",
        name="Single-Use Bioreactor 2000L",
        category="Bioprocessing",
        criticality="LIFE_CRITICAL",
        batch_value_usd=750000.0,
        facility="Biologics Pilot Plant C",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=5.0, nominal_high=18.0, warning_high=32.0, critical_high=50.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=35.0, nominal_high=38.0, warning_high=42.0, critical_high=50.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=0.05, nominal_high=0.3, warning_high=0.8, critical_high=1.5),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=22.0, warning_high=35.0, critical_high=52.0),
            "motor_rpm": SensorThreshold(unit="RPM", min_physical=0.0, max_physical=3000.0, nominal_low=40.0, nominal_high=250.0, warning_high=350.0, critical_high=500.0),
        },
        description="Mammalian cell culture bioreactor producing anti-HER2 monoclonal antibodies.",
    ),
    "TFF-SKID-01": EquipmentProfile(
        equipment_id="TFF-SKID-01",
        name="Tangential Flow Filtration Skid",
        category="Bioprocessing",
        criticality="CRITICAL",
        batch_value_usd=320000.0,
        facility="Biologics Pilot Plant C",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=10.0, nominal_high=26.0, warning_high=42.0, critical_high=62.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=4.0, nominal_high=22.0, warning_high=30.0, critical_high=45.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=1.5, nominal_high=3.5, warning_high=5.0, critical_high=7.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=12.0, nominal_high=30.0, warning_high=45.0, critical_high=65.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=40.0, nominal_high=150.0, warning_high=210.0, critical_high=280.0),
        },
        description="Ultrafiltration / Diafiltration skid for protein concentration.",
    ),
    "CHROM-SKID-01": EquipmentProfile(
        equipment_id="CHROM-SKID-01",
        name="Preparative Chromatography Skid",
        category="Bioprocessing",
        criticality="CRITICAL",
        batch_value_usd=400000.0,
        facility="Biologics Pilot Plant C",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=22.0, warning_high=36.0, critical_high=54.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=4.0, nominal_high=18.0, warning_high=26.0, critical_high=38.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=2.0, nominal_high=4.5, warning_high=6.0, critical_high=8.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=10.0, nominal_high=28.0, warning_high=42.0, critical_high=60.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=20.0, nominal_high=120.0, warning_high=170.0, critical_high=230.0),
        },
        description="Protein A affinity and ion-exchange preparative purification skid.",
    ),
    "CIP-SYSTEM-01": EquipmentProfile(
        equipment_id="CIP-SYSTEM-01",
        name="Clean-In-Place Recirculation Unit",
        category="Bioprocessing",
        criticality="HIGH",
        batch_value_usd=60000.0,
        facility="Biologics Pilot Plant C",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=12.0, nominal_high=30.0, warning_high=48.0, critical_high=68.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=60.0, nominal_high=85.0, warning_high=95.0, critical_high=110.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=2.5, nominal_high=4.8, warning_high=6.2, critical_high=8.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=18.0, nominal_high=40.0, warning_high=58.0, critical_high=78.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=150.0, nominal_high=350.0, warning_high=420.0, critical_high=480.0),
        },
        description="Multi-tank automated caustic/acid/WFI CIP sanitization skid.",
    ),

    # -- 4. Analytical Quality Control Lab -------------------
    "HPLC-AUTO-01": EquipmentProfile(
        equipment_id="HPLC-AUTO-01",
        name="UPLC Quaternary Solvent Pump",
        category="Analytical Lab",
        criticality="HIGH",
        batch_value_usd=45000.0,
        facility="Central Quality Control Lab",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=2.0, nominal_high=10.0, warning_high=18.0, critical_high=30.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=18.0, nominal_high=30.0, warning_high=42.0, critical_high=55.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=1000.0, nominal_low=200.0, nominal_high=600.0, warning_high=750.0, critical_high=900.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=50.0, nominal_low=2.0, nominal_high=8.0, warning_high=14.0, critical_high=22.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=10.0, nominal_low=0.2, nominal_high=1.5, warning_high=2.5, critical_high=4.0),
        },
        description="Ultra-high performance liquid chromatography pump for batch release testing.",
    ),
    "LCMS-CHAMBER-01": EquipmentProfile(
        equipment_id="LCMS-CHAMBER-01",
        name="LC-MS/MS Triple Quadrupole Chamber",
        category="Analytical Lab",
        criticality="CRITICAL",
        batch_value_usd=180000.0,
        facility="Central Quality Control Lab",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=1.0, nominal_high=8.0, warning_high=15.0, critical_high=25.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=350.0, nominal_low=150.0, nominal_high=280.0, warning_high=310.0, critical_high=340.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=5.0, nominal_low=0.0001, nominal_high=0.01, warning_high=0.05, critical_high=0.2),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=50.0, nominal_low=8.0, nominal_high=22.0, warning_high=32.0, critical_high=44.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=50.0, nominal_low=2.0, nominal_high=12.0, warning_high=18.0, critical_high=26.0),
        },
        description="High-sensitivity mass spectrometry chamber with turbomolecular vacuum pump.",
    ),
    "SPECTRO-UV-01": EquipmentProfile(
        equipment_id="SPECTRO-UV-01",
        name="UV-Vis Double Beam Spectrophotometer",
        category="Analytical Lab",
        criticality="MEDIUM",
        batch_value_usd=25000.0,
        facility="Central Quality Control Lab",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=0.5, nominal_high=5.0, warning_high=10.0, critical_high=18.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=100.0, nominal_low=18.0, nominal_high=28.0, warning_high=38.0, critical_high=48.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=20.0, nominal_low=1.0, nominal_high=4.5, warning_high=7.0, critical_high=10.0),
            "optical_transmittance": SensorThreshold(unit="%", min_physical=0.0, max_physical=100.0, nominal_low=85.0, nominal_high=99.5, warning_high=75.0, critical_high=60.0),
            "pulse_count": SensorThreshold(unit="count", min_physical=0.0, max_physical=50000.0, nominal_low=1000.0, nominal_high=20000.0, warning_high=30000.0, critical_high=42000.0),
        },
        description="Quantitative spectrophotometer with deuterium lamp health tracking.",
    ),
    "DISSOLUTION-01": EquipmentProfile(
        equipment_id="DISSOLUTION-01",
        name="Automated USP Dissolution Tester",
        category="Analytical Lab",
        criticality="HIGH",
        batch_value_usd=50000.0,
        facility="Central Quality Control Lab",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=2.0, nominal_high=8.0, warning_high=16.0, critical_high=26.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=100.0, nominal_low=36.5, nominal_high=37.5, warning_high=39.0, critical_high=42.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=30.0, nominal_low=3.0, nominal_high=9.0, warning_high=14.0, critical_high=20.0),
            "motor_rpm": SensorThreshold(unit="RPM", min_physical=0.0, max_physical=500.0, nominal_low=48.0, nominal_high=102.0, warning_high=120.0, critical_high=150.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=20.0, nominal_low=0.5, nominal_high=2.5, warning_high=4.0, critical_high=6.0),
        },
        description="8-vessel automated dissolution bath for oncology tablet bioavailability testing.",
    ),

    # -- 5. Hospital Oncology Clinical Facilities ------------
    "LINAC-01": EquipmentProfile(
        equipment_id="LINAC-01",
        name="Varian TrueBeam Linear Accelerator",
        category="Hospital Oncology",
        criticality="LIFE_CRITICAL",
        batch_value_usd=1200000.0,
        facility="Zydus Comprehensive Cancer Center",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=4.0, nominal_high=16.0, warning_high=28.0, critical_high=46.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=0.0, max_physical=120.0, nominal_low=20.0, nominal_high=32.0, warning_high=42.0, critical_high=55.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=2.5, nominal_high=4.2, warning_high=5.5, critical_high=7.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=20.0, nominal_high=55.0, warning_high=75.0, critical_high=92.0),
            "beam_current_ma": SensorThreshold(unit="mA", min_physical=0.0, max_physical=500.0, nominal_low=50.0, nominal_high=220.0, warning_high=280.0, critical_high=360.0),
        },
        description="High-precision photon/electron radiotherapy machine for cancer patient treatments.",
    ),
    "CYCLOTRON-01": EquipmentProfile(
        equipment_id="CYCLOTRON-01",
        name="Medical PET Radioisotope Cyclotron",
        category="Hospital Oncology",
        criticality="LIFE_CRITICAL",
        batch_value_usd=900000.0,
        facility="Zydus Comprehensive Cancer Center",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=8.0, nominal_high=22.0, warning_high=38.0, critical_high=56.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=-50.0, max_physical=100.0, nominal_low=-20.0, nominal_high=25.0, warning_high=40.0, critical_high=58.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=10.0, nominal_low=0.0001, nominal_high=0.05, warning_high=0.2, critical_high=1.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=150.0, nominal_low=40.0, nominal_high=95.0, warning_high=120.0, critical_high=140.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=500.0, nominal_low=100.0, nominal_high=280.0, warning_high=350.0, critical_high=420.0),
        },
        description="Particle accelerator producing FDG-18 radiotracers for PET oncology scans.",
    ),
    "MRI-CRYO-01": EquipmentProfile(
        equipment_id="MRI-CRYO-01",
        name="3T MRI Superconducting Cryocooler",
        category="Hospital Oncology",
        criticality="LIFE_CRITICAL",
        batch_value_usd=800000.0,
        facility="Zydus Comprehensive Cancer Center",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=10.0, nominal_high=25.0, warning_high=40.0, critical_high=60.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=-273.0, max_physical=50.0, nominal_low=-269.0, nominal_high=-265.0, warning_high=-255.0, critical_high=-240.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=30.0, nominal_low=14.0, nominal_high=19.0, warning_high=22.5, critical_high=26.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=100.0, nominal_low=15.0, nominal_high=35.0, warning_high=50.0, critical_high=70.0),
            "flow_rate_lpm": SensorThreshold(unit="L/min", min_physical=0.0, max_physical=200.0, nominal_low=20.0, nominal_high=65.0, warning_high=85.0, critical_high=110.0),
        },
        description="Liquid helium refrigeration coldhead maintaining 4 Kelvin superconducting coil.",
    ),
    "ULT-FREEZER-01": EquipmentProfile(
        equipment_id="ULT-FREEZER-01",
        name="-80C Cryopreservation Biobank Vault",
        category="Hospital Oncology",
        criticality="LIFE_CRITICAL",
        batch_value_usd=500000.0,
        facility="Zydus Comprehensive Cancer Center",
        sensors={
            "vibration_hz": SensorThreshold(unit="Hz", min_physical=0.0, max_physical=100.0, nominal_low=4.0, nominal_high=16.0, warning_high=28.0, critical_high=45.0),
            "temperature_c": SensorThreshold(unit="C", min_physical=-100.0, max_physical=50.0, nominal_low=-86.0, nominal_high=-78.0, warning_high=-68.0, critical_high=-55.0),
            "pressure_bar": SensorThreshold(unit="bar", min_physical=0.0, max_physical=25.0, nominal_low=10.0, nominal_high=16.0, warning_high=19.5, critical_high=23.0),
            "current_draw_a": SensorThreshold(unit="A", min_physical=0.0, max_physical=50.0, nominal_low=6.0, nominal_high=18.0, warning_high=26.0, critical_high=38.0),
            "door_open_sec": SensorThreshold(unit="sec", min_physical=0.0, max_physical=600.0, nominal_low=0.0, nominal_high=30.0, warning_high=90.0, critical_high=180.0),
        },
        description="Dual-cascade cascade compressor biobank storing clinical cancer biopsy samples.",
    ),
}


def get_equipment_profile(equipment_id: str) -> Optional[EquipmentProfile]:
    return EQUIPMENT_DIRECTORY.get(equipment_id)


def list_all_equipment_ids() -> List[str]:
    return list(EQUIPMENT_DIRECTORY.keys())


def resolve_equipment_id(name_or_id: str | int) -> int:
    """Maps equipment name/code to its database primary key integer."""
    from common.equipment_registry import resolve_equipment_id as reg_resolve
    return reg_resolve(name_or_id)
