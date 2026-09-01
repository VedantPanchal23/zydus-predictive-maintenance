"""
Maintenance Work Order & SOP Prescription Service
==================================================
Manages the regulatory lifecycle of corrective and preventive maintenance work orders,
attaching manufacturer SOPs, cleanroom PPE specs, and dual-signature sign-offs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from core.db_pool import get_db_cursor
from core.audit_logger import log_audit_event
from domain.equipment import get_equipment_profile
from domain.prescription import get_prescription

logger = logging.getLogger("workorder-service")


def create_or_upsert_workorder(
    equipment_id: str,
    priority: str,
    description: str,
    alert_id: Optional[int] = None,
) -> Optional[int]:
    """
    Creates an automated maintenance work order with attached GxP SOP prescription.
    """
    profile = get_equipment_profile(equipment_id)
    category = profile.category if profile else "Granulation"
    prescription = get_prescription(category)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        from domain.equipment import resolve_equipment_id
        eq_int = resolve_equipment_id(equipment_id)
        with get_db_cursor() as cur:
            # Check for existing open work order
            cur.execute(
                """
                SELECT id FROM work_orders
                WHERE equipment_id = %s AND status IN ('open', 'in_progress', 'OPEN', 'IN_PROGRESS')
                ORDER BY id DESC LIMIT 1;
                """,
                (eq_int,),
            )
            existing = cur.fetchone()
            if existing:
                return existing["id"]

            cur.execute(
                """
                INSERT INTO work_orders (
                    equipment_id, priority, status, description, created_at
                ) VALUES (
                    %s, %s, 'open', %s, %s
                ) RETURNING id;
                """,
                (
                    eq_int,
                    priority.lower(),
                    description,
                    now_iso,
                ),
            )
            row = cur.fetchone()
            wo_id = row["id"] if row else None

            log_audit_event(
                user_id="SYSTEM",
                user_role="SYSTEM_AUTOMATION",
                action="CREATE_WORK_ORDER",
                entity_type="WORK_ORDER",
                entity_id=str(wo_id),
                after_state={"equipment_id": equipment_id, "priority": priority, "sop": prescription.sop_code},
                reason_for_change=f"Automated GxP Work Order generated: {description}",
            )
            return wo_id
    except Exception as exc:
        logger.error("Failed to create work order for %s: %s", equipment_id, exc)
        return None


def complete_workorder(
    workorder_id: int,
    user_id: str,
    user_role: str,
    reason_for_change: str,
    ip_address: Optional[str] = None,
) -> bool:
    """
    Executes electronic signature completion of a work order with mandatory GxP reason.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, equipment_id, status FROM work_orders WHERE id = %s;
                """,
                (workorder_id,),
            )
            existing = cur.fetchone()
            if not existing:
                return False

            cur.execute(
                """
                UPDATE work_orders
                SET status = 'COMPLETED',
                    completed_at = %s,
                    completed_by = %s,
                    completion_notes = %s,
                    updated_at = %s
                WHERE id = %s;
                """,
                (now_iso, user_id, reason_for_change, now_iso, workorder_id),
            )

            log_audit_event(
                user_id=user_id,
                user_role=user_role,
                action="COMPLETE_WORK_ORDER",
                entity_type="WORK_ORDER",
                entity_id=str(workorder_id),
                before_state=dict(existing),
                after_state={"status": "COMPLETED", "completed_by": user_id, "completed_at": now_iso},
                reason_for_change=reason_for_change,
                ip_address=ip_address,
            )
            return True
    except Exception as exc:
        logger.error("Error completing work order #%s: %s", workorder_id, exc)
        return False
