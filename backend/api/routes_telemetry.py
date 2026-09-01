"""
REST API: Telemetry Ingestion & Dead Letter Queue
=================================================
Provides HTTP endpoints for raw telemetry ingest and DLQ error inspection.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.auth import get_current_user, require_role
from core.db_pool import get_db_cursor
from core.metrics import metrics
from domain.telemetry import RawSensorReading, BatchTelemetryPayload, IngestionResult
from domain.equipment import resolve_equipment_id
from ingestion.validator import validate_sensor_reading
from ingestion.dlq import record_to_dlq, get_dlq_records

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry Ingest & DLQ"])


@router.post("/ingest", response_model=IngestionResult)
async def ingest_telemetry_batch(
    payload: BatchTelemetryPayload,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Ingests a batch of raw sensor readings with schema & physical range validation.
    Corrupt or out-of-range readings are automatically routed to the Dead Letter Queue.
    """
    t0 = time.time()
    valid_records = []
    rejected_count = 0

    for reading in payload.readings:
        is_valid, err = validate_sensor_reading(reading)
        if is_valid:
            eq_int = resolve_equipment_id(reading.equipment_id)
            valid_records.append((
                eq_int,
                reading.sensor_name,
                reading.value,
                reading.unit,
                reading.timestamp or datetime.now(timezone.utc),
            ))
        else:
            rejected_count += 1
            record_to_dlq(
                equipment_id=reading.equipment_id,
                sensor_name=reading.sensor_name,
                raw_payload=reading.model_dump(),
                error_reason=err or "Validation failure",
                source="http_api",
            )

    if valid_records:
        try:
            with get_db_cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, timestamp)
                    VALUES %s;
                    """,
                    valid_records,
                )
            metrics.inc_ingest(len(valid_records))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Database batch insertion failed: {exc}")

    elapsed_ms = (time.time() - t0) * 1000.0
    return IngestionResult(
        accepted=len(valid_records),
        rejected=rejected_count,
        dlq_count=rejected_count,
        elapsed_ms=round(elapsed_ms, 2),
    )


@router.get("/dlq", dependencies=[Depends(require_role(["admin", "engineer", "auditor"]))])
async def list_dlq_records(limit: int = 50):
    """Retrieves recent Dead Letter Queue error records."""
    records = get_dlq_records(limit=limit)
    return {"dlq_records": records, "count": len(records)}
