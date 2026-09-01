"""
Domain Model: Telemetry & Ingestion Schemas
===========================================
Pydantic v2 models for raw sensor readings, micro-batch payloads, and validated metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RawSensorReading(BaseModel):
    equipment_id: str = Field(..., min_length=2, max_length=50)
    sensor_name: str = Field(..., min_length=2, max_length=50)
    value: float
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class BatchTelemetryPayload(BaseModel):
    readings: List[RawSensorReading]


class IngestionResult(BaseModel):
    accepted: int
    rejected: int
    dlq_count: int
    elapsed_ms: float
