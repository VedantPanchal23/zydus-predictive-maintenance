"""
Domain Model: GAMP 5 Batch Spoilage & Clinical Impact Assessment
================================================================
Calculates financial batch spoilage risk in $USD, sterility breach probability,
and clinical containment recommendations based on equipment health degradation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel
from domain.equipment import get_equipment_profile


class ImpactAssessment(BaseModel):
    batch_value_usd: float
    expected_financial_loss_usd: float
    sterility_breach_probability: float  # 0.0 to 1.0
    clinical_risk_tier: str              # NEGLIGIBLE, MODERATE, CRITICAL, LIFE_SAFETY
    recommended_containment_action: str
    patient_impact_summary: str


def assess_equipment_impact(
    equipment_id: str,
    failure_probability: float,
    anomaly_score: float,
    days_to_failure: float,
) -> ImpactAssessment:
    """
    Computes rigorous GAMP 5 regulatory & financial impact metrics.
    """
    profile = get_equipment_profile(equipment_id)
    batch_val = profile.batch_value_usd if profile else 100000.0
    category = profile.category if profile else "General"
    crit = profile.criticality if profile else "HIGH"

    # Expected Loss = Batch Value * Failure Probability * Anomaly Factor
    combined_risk = max(failure_probability, anomaly_score * 0.9)
    loss_usd = round(batch_val * min(1.0, combined_risk * 1.1), 2)

    # Sterility Breach probability calculation
    if category in ("Sterile Injectables", "Bioprocessing"):
        sterility_risk = round(min(1.0, failure_probability * 0.95 + (0.3 if days_to_failure < 3.0 else 0.05)), 4)
    else:
        sterility_risk = 0.0

    # Risk Tier & Containment
    if crit == "LIFE_CRITICAL" and combined_risk >= 0.70:
        risk_tier = "LIFE_SAFETY"
        if category == "Hospital Oncology":
            containment = "IMMEDIATE CLINICAL SHUTDOWN: Divert oncology patients to backup radiation suite. Execute full dosimetry audit."
            patient_summary = "Patient safety risk: Potential beam geometry variance or radiotracer synthesis abort."
        else:
            containment = "IMMEDIATE BATCH QUARANTINE: Isolate current aseptic batch in Class A barrier. Initiate full sterility validation protocol."
            patient_summary = "High sterility breach probability. Potential commercial sterile injectable contamination."
    elif combined_risk >= 0.70 or days_to_failure < 3.0:
        risk_tier = "CRITICAL"
        containment = "SCHEDULE EMERGENCY MAINTENANCE: Halt production at end of current cycle. Dispatch maintenance team under GxP SOP."
        patient_summary = "Elevated risk of product defect or out-of-specification tablet dissolution."
    elif combined_risk >= 0.40 or days_to_failure < 14.0:
        risk_tier = "MODERATE"
        containment = "INCREASE SENSOR POLLING & MONITORING: Perform routine vibration analysis and visual inspection during shift handover."
        patient_summary = "Minor operational variance. No immediate patient impact."
    else:
        risk_tier = "NEGLIGIBLE"
        containment = "NORMAL GXP OPERATIONS: Machine operating within nominal validation parameters."
        patient_summary = "Nominal operating state. Zero clinical risk."

    return ImpactAssessment(
        batch_value_usd=batch_val,
        expected_financial_loss_usd=loss_usd,
        sterility_breach_probability=sterility_risk,
        clinical_risk_tier=risk_tier,
        recommended_containment_action=containment,
        patient_impact_summary=patient_summary,
    )
