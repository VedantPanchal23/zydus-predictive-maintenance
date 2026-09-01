import pytest
from incident.state_machine import EquipmentStateMachine
from domain.impact import assess_equipment_impact
from domain.prescription import get_prescription

def test_hysteresis_escalation_and_recovery():
    sm = EquipmentStateMachine(escalation_threshold=2, recovery_threshold=3)

    # 1. First breach -> WATCH
    state1, _ = sm.update_state("TEST-EQ-01", failure_probability=0.45, anomaly_score=0.40, days_to_failure=12.0)
    assert state1 == "WATCH"

    # 2. Second breach -> WARNING
    state2, _ = sm.update_state("TEST-EQ-01", failure_probability=0.50, anomaly_score=0.50, days_to_failure=10.0)
    assert state2 == "WARNING"

    # 3. Third critical breach -> CRITICAL
    state3, _ = sm.update_state("TEST-EQ-01", failure_probability=0.85, anomaly_score=0.90, days_to_failure=2.0)
    state4, _ = sm.update_state("TEST-EQ-01", failure_probability=0.88, anomaly_score=0.92, days_to_failure=1.5)
    assert state4 == "CRITICAL"

    # 4. Recovery requires 3 consecutive healthy cycles
    sm.update_state("TEST-EQ-01", failure_probability=0.05, anomaly_score=0.10, days_to_failure=50.0)
    sm.update_state("TEST-EQ-01", failure_probability=0.05, anomaly_score=0.10, days_to_failure=50.0)
    rec_state, _ = sm.update_state("TEST-EQ-01", failure_probability=0.05, anomaly_score=0.10, days_to_failure=50.0)
    assert rec_state == "NORMAL"

def test_gamp5_impact_quantification():
    impact = assess_equipment_impact("VIAL-FILL-01", failure_probability=0.85, anomaly_score=0.90, days_to_failure=1.5)
    assert impact.clinical_risk_tier == "LIFE_SAFETY"
    assert impact.sterility_breach_probability > 0.50
    assert impact.expected_financial_loss_usd > 200000.0
    assert "IMMEDIATE BATCH QUARANTINE" in impact.recommended_containment_action

def test_prescription_dispatcher():
    presc = get_prescription("Sterile Injectables")
    assert presc.sop_code == "SOP-MNT-STER-701"
    assert len(presc.cleanroom_ppe) > 0
    assert presc.dual_signoff_required is True
