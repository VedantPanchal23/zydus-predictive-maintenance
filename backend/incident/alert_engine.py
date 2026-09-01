"""
Automated Alert Engine & Cooldown Deduplication
===============================================
Evaluates predictive telemetry across all active assets, applies hysteresis state
filtering, calculates GAMP 5 impact risk, and auto-dispatches maintenance work orders.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import redis as redis_lib

from core.config import REDIS_URL, CRITICAL_ALERT_COOLDOWN_HOURS, WARNING_ALERT_COOLDOWN_HOURS
from core.db_pool import get_db_cursor
from core.audit_logger import log_audit_event
from domain.equipment import list_all_equipment_ids, get_equipment_profile
from domain.impact import assess_equipment_impact
from incident.state_machine import state_machine
from incident.workorder_service import create_or_upsert_workorder

logger = logging.getLogger("alert-engine")


def is_prediction_stale(prediction: Dict[str, Any], max_age_minutes: int = 10) -> bool:
    pred_ts = prediction.get("predicted_at")
    if not pred_ts:
        return True
    try:
        if isinstance(pred_ts, str):
            dt = datetime.fromisoformat(pred_ts.replace("Z", "+00:00"))
        else:
            dt = pred_ts
        return (datetime.now(timezone.utc) - dt) > timedelta(minutes=max_age_minutes)
    except Exception:
        return True


def evaluate_alerts_for_equipment(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Evaluates alerts for a single asset based on its latest prediction.
    """
    try:
        from domain.equipment import resolve_equipment_id
        eq_int = resolve_equipment_id(equipment_id)
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT anomaly_score, failure_probability, days_to_failure, confidence, predicted_at
                FROM predictions
                WHERE equipment_id = %s
                ORDER BY predicted_at DESC LIMIT 1;
                """,
                (eq_int,),
            )
            pred = cur.fetchone()

        if not pred or is_prediction_stale(pred):
            return None

        fail_prob = float(pred["failure_probability"])
        anomaly_score = float(pred["anomaly_score"])
        days_to_fail = float(pred["days_to_failure"])

        # Update Hysteresis State Machine
        curr_state, changed = state_machine.update_state(
            equipment_id=equipment_id,
            failure_probability=fail_prob,
            anomaly_score=anomaly_score,
            days_to_failure=days_to_fail,
        )

        if curr_state not in ("WARNING", "CRITICAL"):
            return None

        # Check Active Alert / Cooldown in Database
        cooldown_hours = CRITICAL_ALERT_COOLDOWN_HOURS if curr_state == "CRITICAL" else WARNING_ALERT_COOLDOWN_HOURS
        cooldown_cutoff = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)

        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, severity, created_at
                FROM alerts
                WHERE equipment_id = %s AND (acknowledged_at IS NULL OR created_at >= %s)
                ORDER BY id DESC LIMIT 1;
                """,
                (eq_int, cooldown_cutoff.isoformat()),
            )
            existing_alert = cur.fetchone()

        if existing_alert:
            # Already alerted or within cooldown window
            return None

        # GAMP 5 Impact Assessment
        impact = assess_equipment_impact(equipment_id, fail_prob, anomaly_score, days_to_fail)
        profile = get_equipment_profile(equipment_id)
        asset_name = profile.name if profile else equipment_id

        msg = (
            f"Asset {equipment_id} ({asset_name}) entered {curr_state} state: "
            f"Failure Prob: {fail_prob:.1%}, Est RUL: {days_to_fail:.1f} days. "
            f"Financial Loss Risk: ${impact.expected_financial_loss_usd:,.2f} USD."
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (
                    equipment_id, severity, message, created_at
                ) VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    eq_int,
                    curr_state,
                    msg,
                    now_iso,
                ),
            )
            row = cur.fetchone()
            alert_id = row["id"] if row else None

        # Auto-create Critical Work Order if in CRITICAL state
        if curr_state == "CRITICAL" and alert_id:
            wo_id = create_or_upsert_workorder(
                equipment_id=equipment_id,
                priority="CRITICAL",
                description=f"Auto-generated for Critical Alert #{alert_id}: {msg}",
                alert_id=alert_id,
            )

        alert_payload = {
            "alert_id": alert_id,
            "equipment_id": equipment_id,
            "severity": curr_state,
            "message": msg,
            "impact": impact.model_dump(),
            "created_at": now_iso,
        }

        # Publish to Redis Live Channel
        try:
            r = redis_lib.from_url(REDIS_URL, socket_timeout=2)
            r.publish("alerts:live", json.dumps(alert_payload, default=str))
        except Exception:
            pass

        return alert_payload
    except Exception as exc:
        logger.error("Error evaluating alerts for %s: %s", equipment_id, exc)
        return None


def run_alert_engine() -> Dict[str, Any]:
    """Evaluates alerts across all 20 assets."""
    all_eq = list_all_equipment_ids()
    generated = 0
    for eq_id in all_eq:
        res = evaluate_alerts_for_equipment(eq_id)
        if res:
            generated += 1
    return {"alerts_evaluated": len(all_eq), "new_alerts": generated}

def build_alert_classification(prediction: dict) -> dict | None:
    fail_prob = float(prediction.get("failure_probability", 0.0))
    anomaly_score = float(prediction.get("anomaly_score", 0.0))
    days_to_fail = float(prediction.get("days_to_failure", 30.0))
    
    if (fail_prob >= 0.80 and anomaly_score >= 0.80) or days_to_fail <= 3.0 or fail_prob >= 0.85:
        return {
            "severity": "CRITICAL",
            "create_work_order": True,
            "cooldown_hours": 6,
            "message": "Critical risk escalation: Failure probability is acute. Immediate inspection required.",
        }
    elif (fail_prob >= 0.40 and days_to_fail <= 45.0) or days_to_fail <= 14.0:
        return {
            "severity": "WARNING",
            "create_work_order": False,
            "cooldown_hours": 2,
            "message": "Moderate degradation detected: Elevated failure probability. Monitor closely.",
        }
    return None
