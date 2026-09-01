"""
Dead Letter Queue (DLQ) Manager
===============================
Captures malformed, corrupt, or out-of-range sensor readings into telemetry_dlq
table for error inspection, root-cause forensics, and automated alerting.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

from core.db_pool import get_db_cursor
from core.metrics import metrics

logger = logging.getLogger("telemetry-dlq")


def record_to_dlq(
    equipment_id: Optional[str],
    sensor_name: Optional[str],
    raw_payload: Any,
    error_reason: str,
    source: str = "kafka",
) -> Optional[int]:
    """
    Inserts a rejected telemetry record into the Dead Letter Queue table.
    """
    metrics.inc_dlq(1)
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO telemetry_dlq (
                    equipment_id, sensor_name, raw_payload, error_reason, source, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    equipment_id or "UNKNOWN",
                    sensor_name or "UNKNOWN",
                    json.dumps(raw_payload, default=str),
                    error_reason,
                    source,
                    ts,
                ),
            )
            row = cur.fetchone()
            dlq_id = row["id"] if row else None
            logger.warning(
                "Telemetry routed to DLQ [#%s] | Equipment: %s | Sensor: %s | Reason: %s",
                dlq_id,
                equipment_id,
                sensor_name,
                error_reason,
            )
            return dlq_id
    except Exception as exc:
        logger.error("Failed to record telemetry to DLQ: %s", exc)
        return None


def get_dlq_records(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent DLQ records for diagnostic inspection."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, equipment_id, sensor_name, raw_payload, error_reason, source, created_at
                FROM telemetry_dlq
                ORDER BY id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cur.fetchall() or []
    except Exception as exc:
        logger.error("Error fetching DLQ records: %s", exc)
        return []
