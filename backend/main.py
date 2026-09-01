"""
Zydus Pharma Oncology � Predictive Maintenance API
=====================================================
Complete REST API + WebSocket Server (Enterprise Production).
"""

import os
import json
import logging
import math
import threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List, Any

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import redis as redis_lib
import psycopg2.extras

from auth.auth import router as auth_router, get_current_user, require_role
from common.db_pool import get_db_cursor, init_pool, close_pool
from common.audit_logger import log_audit_event
from common.risk_guidance import classify_equipment_risk
from websocket.live import router as ws_router, start_broadcaster, stop_broadcaster

# -- Logging -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zydus-backend")

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# -- Kafka consumer instance ---------------------------------
_consumer = None


def _startup_kafka():
    global _consumer
    try:
        from kafka_utils.create_topics import create_topics
        create_topics()
    except Exception as e:
        logger.error(f"Failed to create Kafka topics: {e}")
    try:
        from ingestion.kafka_consumer import SensorDataConsumer
        _consumer = SensorDataConsumer()
        _consumer.start()
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer: {e}")


# -- Lifespan ------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Zydus Predictive Maintenance Enterprise Backend...")
    init_pool()
    try:
        from db.bootstrap import bootstrap_database_if_needed
        bootstrap_database_if_needed()
    except Exception as exc:
        logger.warning("Database bootstrap warning: %s", exc)

    start_broadcaster()
    try:
        from ml.scheduler import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("ML scheduler startup warning: %s", exc)

    kafka_thread = threading.Thread(target=_startup_kafka, daemon=True, name="kafka-setup")
    kafka_thread.start()
    logger.info("Backend initialized and ready for traffic")
    yield
    logger.info("Shutting down...")
    try:
        from ml.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    stop_broadcaster()
    if _consumer:
        _consumer.stop()
    close_pool()


# -- FastAPI App ---------------------------------------------
app = FastAPI(
    title="Zydus Predictive Maintenance API",
    description="AI-powered condition monitoring & predictive maintenance for Zydus Pharma Oncology assets (21 CFR Part 11 Compliant)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes_telemetry import router as telemetry_router
from api.routes_metrics import router as metrics_router
from api.routes_audit import router as audit_router

# Include routers
app.include_router(auth_router)
app.include_router(ws_router)
app.include_router(telemetry_router)
app.include_router(metrics_router)
app.include_router(audit_router)


# -- Redis helper --------------------------------------------
def get_redis():
    try:
        r = redis_lib.from_url(REDIS_URL)
        r.ping()
        return r
    except Exception:
        return None


def error_response(code: int, message: str):
    raise HTTPException(status_code=code, detail={"error": True, "message": message, "code": code})


# -- Pydantic Schemas ----------------------------------------
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    pages: int


class WorkOrderCompleteRequest(BaseModel):
    completion_notes: Optional[str] = None
    reason_for_change: Optional[str] = "Preventive/Corrective Maintenance Completed"


class AlertAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None


# ------------------------------------------------------------
#  PUBLIC ENDPOINTS (no auth)
# ------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "zydus-backend", "version": "2.0.0"}


@app.get("/")
def root():
    return {"message": "Zydus Pharma Oncology - Predictive Maintenance Enterprise Platform"}


# ------------------------------------------------------------
#  EQUIPMENT METADATA & ENRICHMENT
# ------------------------------------------------------------

EQUIPMENT_METADATA = {
    "GRAN-LINE-01": {"display_name": "High Shear Mixer Granulator 600L", "category": "Granulation", "facility": "Oral Solid Dosage Block A", "batch_value_inr": 2500000},
    "TABLET-PRESS-01": {"display_name": "High Speed Rotary Tablet Press", "category": "Compression", "facility": "Oral Solid Dosage Block A", "batch_value_inr": 3200000},
    "BLISTER-PACK-01": {"display_name": "High-Speed Blister Packaging Line", "category": "Packaging", "facility": "Oral Solid Dosage Block A", "batch_value_inr": 1800000},
    "CAPSULE-FILL-01": {"display_name": "Automatic Capsule Filling Machine", "category": "Encapsulation", "facility": "Oral Solid Dosage Block A", "batch_value_inr": 2200000},
    "COATING-DRUM-01": {"display_name": "Perforated Pan Tablet Auto-Coater", "category": "Coating", "facility": "Oral Solid Dosage Block A", "batch_value_inr": 2800000},
    "VIAL-WASHER-01": {"display_name": "Rotary Ultrasonic Vial Washer", "category": "Sterile Washing", "facility": "Sterile Injectable Complex B", "batch_value_inr": 4500000},
    "ASEPTIC-FILL-01": {"display_name": "Aseptic Isolator Liquid Vial Filler", "category": "Aseptic Filling", "facility": "Sterile Injectable Complex B", "batch_value_inr": 8500000},
    "CIP-SKID-01": {"display_name": "Automated Clean-in-Place (CIP) Skid", "category": "Sterilization", "facility": "Sterile Injectable Complex B", "batch_value_inr": 3500000},
    "ULT-FREEZER-01": {"display_name": "Ultra-Low Temperature Freezer (-86°C)", "category": "Cold Storage", "facility": "Biologics Pilot Plant C", "batch_value_inr": 6500000},
    "COLD-ROOM-01": {"display_name": "Vaccine & Biologics Cold Room (2-8°C)", "category": "Cold Chain", "facility": "Biologics Pilot Plant C", "batch_value_inr": 5500000},
    "CHILLER-LOOP-01": {"display_name": "Glycol Process Chiller Loop System", "category": "Thermal Utilities", "facility": "Biologics Pilot Plant C", "batch_value_inr": 4000000},
    "STABILITY-CHAMBER-01": {"display_name": "ICH Photostability Test Chamber", "category": "Stability Testing", "facility": "Biologics Pilot Plant C", "batch_value_inr": 3000000},
    "HPLC-STACK-01": {"display_name": "Quaternary UPLC Chromatography Stack", "category": "Chromatography", "facility": "Central Quality Control Lab", "batch_value_inr": 1500000},
    "LCMS-01": {"display_name": "Triple Quadrupole LC-MS/MS System", "category": "Mass Spectrometry", "facility": "Central Quality Control Lab", "batch_value_inr": 3500000},
    "DISSOLUTION-01": {"display_name": "Automated Tablet Dissolution Apparatus", "category": "Physical QC", "facility": "Central Quality Control Lab", "batch_value_inr": 1200000},
    "TOC-ANALYZER-01": {"display_name": "Total Organic Carbon (TOC) Water Analyzer", "category": "Water Purity", "facility": "Central Quality Control Lab", "batch_value_inr": 1800000},
    "INFUSION-PUMP-01": {"display_name": "Precision Volumetric Infusion System", "category": "Chemotherapy Delivery", "facility": "Zydus Comprehensive Cancer Center", "batch_value_inr": 1200000},
    "SYRINGE-PUMP-01": {"display_name": "Micro-Infusion Oncology Syringe Pump", "category": "Chemotherapy Delivery", "facility": "Zydus Comprehensive Cancer Center", "batch_value_inr": 950000},
    "LINAC-01": {"display_name": "Medical Linear Accelerator (6-18 MeV)", "category": "Radiation Oncology", "facility": "Zydus Comprehensive Cancer Center", "batch_value_inr": 95000000},
    "CT-SCANNER-01": {"display_name": "128-Slice Oncology CT Simulator", "category": "Radiology & Imaging", "facility": "Zydus Comprehensive Cancer Center", "batch_value_inr": 45000000},
}


# ------------------------------------------------------------
#  EQUIPMENT ENDPOINTS
# ------------------------------------------------------------

@app.get("/api/equipment")
def list_equipment(user: dict = Depends(get_current_user)):
    """List all active equipment with current health status and risk guidance."""
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM equipment WHERE status = 'active' ORDER BY id")
        equipments = cur.fetchall()

    r = get_redis()
    result = []
    for eq in equipments:
        health = "unknown"
        fp = None
        anomaly = None
        dtf = None
        eq_name = eq["name"]
        meta = EQUIPMENT_METADATA.get(eq_name, {})
        if r:
            raw = r.get(f"pred:{eq_name}")
            if raw:
                pred = json.loads(raw)
                fp = pred.get("failure_probability")
                anomaly = pred.get("anomaly_score")
                dtf = pred.get("days_to_failure")
                fp_value = float(fp or 0)
                health = "critical" if fp_value > 0.80 else "warning" if fp_value > 0.40 else "healthy"

        risk = classify_equipment_risk(eq["type"], fp, anomaly, dtf)

        result.append({
            "id": eq["id"],
            "equipment_id": eq_name,
            "name": meta.get("display_name", eq_name),
            "type": eq["type"],
            "facility": meta.get("facility", eq.get("location", "Central Block")),
            "category": meta.get("category", eq.get("type", "Manufacturing")),
            "batch_value_inr": meta.get("batch_value_inr", 2500000),
            "location": eq["location"],
            "install_date": eq["install_date"].isoformat() if eq["install_date"] else None,
            "last_maintenance_date": eq["last_maintenance_date"].isoformat() if eq["last_maintenance_date"] else None,
            "status": eq["status"],
            "current_health": health,
            "failure_probability": float(fp) if fp is not None else None,
            "anomaly_score": float(anomaly) if anomaly is not None else None,
            "days_to_failure": float(dtf) if dtf is not None else None,
            "risk_level": risk["risk_level"],
            "risk_reason": risk["risk_reason"],
            "recommended_action": risk["recommended_action"],
        })
    return result


@app.get("/api/equipment/{equipment_id}")
def get_equipment(equipment_id: int, user: dict = Depends(get_current_user)):
    """Single equipment with full detail + latest prediction + open alerts count."""
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM equipment WHERE id = %s", (equipment_id,))
        eq = cur.fetchone()
        if not eq:
            error_response(404, f"Equipment {equipment_id} not found")

        # Latest prediction
        cur.execute("""
            SELECT anomaly_score, failure_probability, days_to_failure, confidence, predicted_at
            FROM predictions WHERE equipment_id = %s ORDER BY predicted_at DESC LIMIT 1
        """, (equipment_id,))
        pred_row = cur.fetchone()

        # Open alerts count
        cur.execute("SELECT COUNT(*) as cnt FROM alerts WHERE equipment_id = %s AND acknowledged_at IS NULL", (equipment_id,))
        alert_count = cur.fetchone()["cnt"]

    prediction = None
    health = "unknown"
    fp = None
    anomaly = None
    dtf = None
    eq_name = eq["name"]
    meta = EQUIPMENT_METADATA.get(eq_name, {})
    if pred_row:
        fp = pred_row["failure_probability"]
        anomaly = pred_row["anomaly_score"]
        dtf = pred_row["days_to_failure"]
        fp_value = float(fp or 0)
        health = "critical" if fp_value > 0.80 else "warning" if fp_value > 0.40 else "healthy"
        prediction = {
            "anomaly_score": round(float(anomaly or 0), 4),
            "failure_probability": round(float(fp_value), 4),
            "days_to_failure": round(float(dtf or 999), 1),
            "confidence": round(float(pred_row["confidence"] or 0), 4),
            "predicted_at": pred_row["predicted_at"].isoformat() if pred_row["predicted_at"] else None,
        }

    risk = classify_equipment_risk(eq["type"], fp, anomaly, dtf)

    return {
        "id": eq["id"],
        "equipment_id": eq_name,
        "name": meta.get("display_name", eq_name),
        "type": eq["type"],
        "facility": meta.get("facility", eq.get("location", "Central Block")),
        "category": meta.get("category", eq.get("type", "Manufacturing")),
        "batch_value_inr": meta.get("batch_value_inr", 2500000),
        "location": eq["location"],
        "install_date": eq["install_date"].isoformat() if eq["install_date"] else None,
        "last_maintenance_date": eq["last_maintenance_date"].isoformat() if eq["last_maintenance_date"] else None,
        "status": eq["status"],
        "current_health": health,
        "latest_prediction": prediction,
        "open_alerts_count": alert_count,
        "risk_level": risk["risk_level"],
        "risk_reason": risk["risk_reason"],
        "recommended_action": risk["recommended_action"],
    }


@app.get("/api/equipment/{equipment_id}/sensors")
def get_equipment_sensors(equipment_id: int, user: dict = Depends(get_current_user)):
    """Last 24 hours of sensor readings grouped by sensor_name."""
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM equipment WHERE id = %s", (equipment_id,))
        if not cur.fetchone():
            error_response(404, f"Equipment {equipment_id} not found")

        cur.execute("""
            SELECT sensor_name, value, unit, timestamp AT TIME ZONE 'UTC' as timestamp
            FROM sensor_readings
            WHERE equipment_id = %s AND timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY timestamp ASC
        """, (equipment_id,))
        rows = cur.fetchall()

    grouped = {}
    for r in rows:
        name = r["sensor_name"]
        if name not in grouped:
            grouped[name] = []
        grouped[name].append({
            "value": round(float(r["value"]), 4),
            "unit": r["unit"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
        })
    return grouped


@app.get("/api/equipment/{equipment_id}/prediction")
def get_equipment_prediction(equipment_id: int, user: dict = Depends(get_current_user)):
    """Latest prediction from Redis cache with PostgreSQL fallback."""
    with get_db_cursor() as cur:
        cur.execute("SELECT name FROM equipment WHERE id = %s", (equipment_id,))
        eq = cur.fetchone()
        if not eq:
            error_response(404, f"Equipment {equipment_id} not found")

    # Check Redis
    r = get_redis()
    if r:
        raw = r.get(f"pred:{eq['name']}")
        if raw:
            return json.loads(raw)

    # Fallback to DB
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT anomaly_score, failure_probability, days_to_failure,
                   confidence, predicted_at
            FROM predictions WHERE equipment_id = %s ORDER BY predicted_at DESC LIMIT 1
        """, (equipment_id,))
        pred = cur.fetchone()

    if not pred:
        return {"message": "No predictions available yet"}

    return {
        "equipment_id": eq["name"],
        "anomaly_score": round(float(pred["anomaly_score"] or 0), 4),
        "failure_probability": round(float(pred["failure_probability"] or 0), 4),
        "days_to_failure": round(float(pred["days_to_failure"] or 999), 1),
        "confidence": round(float(pred["confidence"] or 0), 4),
        "model_version": "production-v1",
        "predicted_at": pred["predicted_at"].isoformat() if pred["predicted_at"] else None,
    }


@app.get("/api/equipment/{equipment_id}/history")
def get_equipment_prediction_history(equipment_id: int, user: dict = Depends(get_current_user)):
    """Last 30 predictions for trend charting."""
    with get_db_cursor() as cur:
        cur.execute("SELECT id FROM equipment WHERE id = %s", (equipment_id,))
        if not cur.fetchone():
            error_response(404, f"Equipment {equipment_id} not found")

        cur.execute("""
            SELECT anomaly_score, failure_probability, days_to_failure,
                   confidence, predicted_at
            FROM predictions WHERE equipment_id = %s
            ORDER BY predicted_at DESC LIMIT 30
        """, (equipment_id,))
        rows = cur.fetchall()

    return [{
        "anomaly_score": round(float(r["anomaly_score"] or 0), 4),
        "failure_probability": round(float(r["failure_probability"] or 0), 4),
        "days_to_failure": round(float(r["days_to_failure"] or 999), 1),
        "confidence": round(float(r["confidence"] or 0), 4),
        "predicted_at": r["predicted_at"].isoformat() if r["predicted_at"] else None,
    } for r in rows]


# ------------------------------------------------------------
#  ALERTS ENDPOINTS
# ------------------------------------------------------------

@app.get("/api/alerts")
def list_alerts(
    severity: str = Query("ALL", description="CRITICAL, WARNING, or ALL"),
    status: str = Query("open", description="open, acknowledged, or ALL"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """List alerts with filtering and pagination."""
    conditions = []
    params = []
    if severity.upper() != "ALL":
        conditions.append("a.severity = %s")
        params.append(severity.upper())
    if status.lower() == "open":
        conditions.append("a.acknowledged_at IS NULL")
    elif status.lower() == "acknowledged":
        conditions.append("a.acknowledged_at IS NOT NULL")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * limit

    with get_db_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) as cnt FROM alerts a {where}", params)  # nosec B608
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT a.id, e.id as equipment_id, e.name as equipment_name, a.severity, a.message,
                   a.created_at AT TIME ZONE 'UTC' as created_at,
                   a.acknowledged_at AT TIME ZONE 'UTC' as acknowledged_at
            FROM alerts a JOIN equipment e ON a.equipment_id = e.id
            {where}
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])  # nosec B608
        rows = cur.fetchall()

    items = [{
        "id": r["id"],
        "equipment_id": r["equipment_id"],
        "equipment_name": r["equipment_name"],
        "severity": r["severity"],
        "message": r["message"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "acknowledged_at": r["acknowledged_at"].isoformat() if r["acknowledged_at"] else None,
    } for r in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@app.patch("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    request: Request,
    body: Optional[AlertAcknowledgeRequest] = None,
    user: dict = Depends(require_role("admin", "engineer")),
):
    """Mark an alert as acknowledged with GxP audit logging."""
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,))
        before_alert = cur.fetchone()
        if not before_alert:
            error_response(404, f"Alert {alert_id} not found")

        cur.execute("""
            UPDATE alerts SET acknowledged_at = NOW()
            WHERE id = %s
            RETURNING id, severity, message,
                      created_at AT TIME ZONE 'UTC' as created_at,
                      acknowledged_at AT TIME ZONE 'UTC' as acknowledged_at
        """, (alert_id,))
        updated = cur.fetchone()

    client_ip = request.client.host if request.client else "unknown"
    log_audit_event(
        user_id=user["username"],
        user_role=user["role"],
        action="ACKNOWLEDGE_ALERT",
        entity_type="ALERT",
        entity_id=alert_id,
        before_state={"acknowledged_at": None},
        after_state={"acknowledged_at": updated["acknowledged_at"].isoformat() if updated["acknowledged_at"] else None},
        reason_for_change=body.notes if body and body.notes else "Engineer acknowledged risk alert",
        ip_address=client_ip,
    )

    return {
        "id": updated["id"],
        "severity": updated["severity"],
        "message": updated["message"],
        "created_at": updated["created_at"].isoformat() if updated["created_at"] else None,
        "acknowledged_at": updated["acknowledged_at"].isoformat() if updated["acknowledged_at"] else None,
    }


# ------------------------------------------------------------
#  WORK ORDERS ENDPOINTS
# ------------------------------------------------------------

@app.get("/api/workorders")
def list_workorders(
    status: str = Query("open", description="open, in_progress, completed, or ALL"),
    user: dict = Depends(get_current_user),
):
    """List work orders with status filtering."""
    where = ""
    params = []
    if status.lower() != "all":
        where = "WHERE wo.status = %s"
        params = [status.lower()]

    with get_db_cursor() as cur:
        cur.execute(f"""
            SELECT wo.id, e.id as equipment_id, e.name as equipment_name, wo.priority, wo.description,
                   wo.predicted_failure_date, wo.status,
                   wo.created_at AT TIME ZONE 'UTC' as created_at,
                   wo.completed_at AT TIME ZONE 'UTC' as completed_at
            FROM work_orders wo JOIN equipment e ON wo.equipment_id = e.id
            {where}
            ORDER BY
                CASE wo.priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                wo.created_at DESC
        """, params)  # nosec B608
        rows = cur.fetchall()

    return [{
        "id": r["id"],
        "equipment_id": r["equipment_id"],
        "equipment_name": r["equipment_name"],
        "priority": r["priority"],
        "description": r["description"],
        "predicted_failure_date": r["predicted_failure_date"].isoformat() if r["predicted_failure_date"] else None,
        "status": r["status"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
    } for r in rows]


@app.patch("/api/workorders/{workorder_id}/complete")
def complete_workorder(
    workorder_id: int,
    request: Request,
    body: Optional[WorkOrderCompleteRequest] = None,
    user: dict = Depends(require_role("admin", "engineer")),
):
    """Mark a work order as completed with GxP audit trail recording."""
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM work_orders WHERE id = %s", (workorder_id,))
        before_wo = cur.fetchone()
        if not before_wo:
            error_response(404, f"Work order {workorder_id} not found")

        cur.execute("""
            UPDATE work_orders SET status = 'completed', completed_at = NOW()
            WHERE id = %s
            RETURNING id, priority, description, status,
                      created_at AT TIME ZONE 'UTC' as created_at,
                      completed_at AT TIME ZONE 'UTC' as completed_at
        """, (workorder_id,))
        updated = cur.fetchone()

    client_ip = request.client.host if request.client else "unknown"
    reason = body.reason_for_change if body and body.reason_for_change else "Maintenance completed and verified"
    notes = body.completion_notes if body and body.completion_notes else None

    log_audit_event(
        user_id=user["username"],
        user_role=user["role"],
        action="COMPLETE_WORK_ORDER",
        entity_type="WORK_ORDER",
        entity_id=workorder_id,
        before_state={"status": before_wo["status"], "completed_at": None},
        after_state={"status": "completed", "completed_at": updated["completed_at"].isoformat(), "notes": notes},
        reason_for_change=reason,
        ip_address=client_ip,
    )

    return {
        "id": updated["id"],
        "priority": updated["priority"],
        "description": updated["description"],
        "status": updated["status"],
        "created_at": updated["created_at"].isoformat() if updated["created_at"] else None,
        "completed_at": updated["completed_at"].isoformat() if updated["completed_at"] else None,
    }




# ------------------------------------------------------------
#  LOGS & SYSTEM METRICS
# ------------------------------------------------------------

@app.get("/api/logs")
def list_logs(
    event_type: str = Query("ALL", description="sensor, prediction, alert, workorder, or ALL"),
    limit: int = Query(50, ge=10, le=200),
    user: dict = Depends(get_current_user),
):
    """Combined operational timeline feed for the frontend logs page."""
    normalized_type = event_type.lower()
    per_source_limit = max(10, min(limit, 100))
    items = []

    with get_db_cursor() as cur:
        if normalized_type in ("all", "sensor"):
            cur.execute("""
                SELECT sr.id, e.name AS equipment_name, sr.sensor_name, sr.value, sr.unit,
                       sr.timestamp AT TIME ZONE 'UTC' AS logged_at
                FROM sensor_readings sr
                JOIN equipment e ON sr.equipment_id = e.id
                ORDER BY sr.timestamp DESC
                LIMIT %s
            """, (per_source_limit,))
            for row in cur.fetchall():
                value = round(float(row["value"]), 4)
                unit = f" {row['unit']}" if row["unit"] else ""
                items.append({
                    "id": f"sensor-{row['id']}",
                    "type": "sensor",
                    "level": "INFO",
                    "equipment_name": row["equipment_name"],
                    "title": row["sensor_name"],
                    "message": f"{row['sensor_name']} reading: {value}{unit}",
                    "timestamp": row["logged_at"].isoformat() if row["logged_at"] else None,
                })

        if normalized_type in ("all", "prediction"):
            cur.execute("""
                SELECT p.id, e.name AS equipment_name, p.anomaly_score, p.failure_probability,
                       p.days_to_failure, p.confidence,
                       p.predicted_at AT TIME ZONE 'UTC' AS logged_at
                FROM predictions p
                JOIN equipment e ON p.equipment_id = e.id
                ORDER BY p.predicted_at DESC
                LIMIT %s
            """, (per_source_limit,))
            for row in cur.fetchall():
                failure_probability = float(row["failure_probability"] or 0)
                level = "CRITICAL" if failure_probability > 0.80 else "WARNING" if failure_probability > 0.40 else "INFO"
                items.append({
                    "id": f"prediction-{row['id']}",
                    "type": "prediction",
                    "level": level,
                    "equipment_name": row["equipment_name"],
                    "title": "Prediction updated",
                    "message": (
                        f"Failure risk {failure_probability * 100:.1f}% | "
                        f"Anomaly {float(row['anomaly_score'] or 0):.3f} | "
                        f"Days to failure {float(row['days_to_failure'] or 999):.1f}"
                    ),
                    "timestamp": row["logged_at"].isoformat() if row["logged_at"] else None,
                })

        if normalized_type in ("all", "alert"):
            cur.execute("""
                SELECT a.id, e.name AS equipment_name, a.severity, a.message,
                       a.created_at AT TIME ZONE 'UTC' AS logged_at
                FROM alerts a
                JOIN equipment e ON a.equipment_id = e.id
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (per_source_limit,))
            for row in cur.fetchall():
                items.append({
                    "id": f"alert-{row['id']}",
                    "type": "alert",
                    "level": row["severity"],
                    "equipment_name": row["equipment_name"],
                    "title": "Alert created",
                    "message": row["message"],
                    "timestamp": row["logged_at"].isoformat() if row["logged_at"] else None,
                })

        if normalized_type in ("all", "workorder"):
            cur.execute("""
                SELECT wo.id, e.name AS equipment_name, wo.priority, wo.status, wo.description,
                       wo.created_at AT TIME ZONE 'UTC' AS logged_at
                FROM work_orders wo
                JOIN equipment e ON wo.equipment_id = e.id
                ORDER BY wo.created_at DESC
                LIMIT %s
            """, (per_source_limit,))
            for row in cur.fetchall():
                items.append({
                    "id": f"workorder-{row['id']}",
                    "type": "workorder",
                    "level": row["priority"] or "INFO",
                    "equipment_name": row["equipment_name"],
                    "title": f"Work order {row['status']}",
                    "message": row["description"],
                    "timestamp": row["logged_at"].isoformat() if row["logged_at"] else None,
                })

    items.sort(key=lambda item: item["timestamp"] or "", reverse=True)
    items = items[:limit]

    return {
        "items": items,
        "total": len(items),
        "limit": limit,
    }


# ------------------------------------------------------------
#  DASHBOARD KPI SUMMARY
# ------------------------------------------------------------

@app.get("/api/dashboard/summary")
def dashboard_summary(user: dict = Depends(get_current_user)):
    """Dashboard KPI summary with connection pooling."""
    with get_db_cursor() as cur:
        cur.execute("SELECT name FROM equipment WHERE status = 'active' ORDER BY id")
        equipment_ids = [row["name"] for row in cur.fetchall()]
        total_equipment = len(equipment_ids)

        cur.execute("SELECT COUNT(*) as cnt FROM alerts WHERE acknowledged_at IS NULL")
        open_alerts = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM alerts WHERE severity = 'CRITICAL' AND acknowledged_at IS NULL")
        critical_alerts = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM work_orders WHERE status = 'open'")
        open_workorders = cur.fetchone()["cnt"]

    # Compute health metrics from Redis cache
    r = get_redis()
    healthy = warning = critical = 0
    scores = []
    for eq_id in equipment_ids:
        if r:
            raw = r.get(f"pred:{eq_id}")
            if raw:
                pred = json.loads(raw)
                fp = float(pred.get("failure_probability") or 0)
                scores.append(1.0 - fp)
                if fp > 0.80:
                    critical += 1
                elif fp > 0.40:
                    warning += 1
                else:
                    healthy += 1
                continue
        healthy += 1

    avg_health = round(sum(scores) / len(scores), 4) if scores else 1.0

    return {
        "total_equipment": total_equipment,
        "healthy_count": healthy,
        "warning_count": warning,
        "critical_count": critical,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "open_workorders": open_workorders,
        "avg_health_score": avg_health,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/chaos/inject")
def inject_chaos_telemetry(
    payload: dict,
    user: dict = Depends(require_role("admin", "engineer")),
):
    """Simulates physical fault telemetry and proves real-time AI & regulatory escalation."""
    from chaos.fault_injector import inject_fault
    eq_id = payload.get("equipment_id", "GRAN-LINE-01")
    fault_type = payload.get("fault_type", "SEIZED_ROTOR")
    user_id = user.get("username", "CHAOS_ENGINEER")
    res = inject_fault(equipment_id=eq_id, fault_type=fault_type, user_id=user_id)
    return res


@app.get("/api/audit-logs/export/pdf")
def export_audit_trail_pdf(
    user: dict = Depends(require_role("admin", "auditor", "engineer")),
):
    """Generates official US FDA 21 CFR Part 11 Regulatory Audit Dossier (PDF)."""
    from fastapi.responses import Response
    from services.pdf_generator import generate_audit_trail_pdf
    
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, user_role, action, entity_type, entity_id,
                   reason_for_change, record_hash, previous_hash, timestamp_utc as timestamp
            FROM audit_logs
            ORDER BY id DESC
            LIMIT 150;
            """
        )
        logs = [dict(r) for r in cur.fetchall()]

    pdf_bytes = generate_audit_trail_pdf(audit_logs=logs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Zydus_21CFR_Audit_Dossier.pdf"},
    )


@app.get("/api/equipment/{equipment_id}/report/pdf")
def export_equipment_report_pdf(
    equipment_id: str,
    user: dict = Depends(get_current_user),
):
    """Generates official Digital Twin Reliability & GAMP 5 Degradation Report (PDF)."""
    from fastapi.responses import Response
    from services.pdf_generator import generate_equipment_report_pdf
    from domain.equipment import resolve_equipment_id

    eq_int = resolve_equipment_id(equipment_id)
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id, name, type, status, location FROM equipment WHERE id = %s;",
            (eq_int,),
        )
        row = cur.fetchone()
        if not row:
            error_response(404, "Equipment not found")
        detail = dict(row)

    meta = EQUIPMENT_METADATA.get(detail["name"], {
        "display_name": detail["name"],
        "facility": detail.get("location") or "Oral Solid Dosage Block A",
        "category": detail.get("type") or "Production",
        "batch_value_inr": 2500000,
    })
    detail["equipment_id"] = detail["name"]
    detail["name"] = meta["display_name"]
    detail["facility"] = meta["facility"]
    detail["category"] = meta["category"]
    detail["batch_value_inr"] = meta["batch_value_inr"]

    # Get latest prediction
    pred = {}
    r = get_redis()
    if r:
        raw = r.get(f"pred:{detail['equipment_id']}")
        if raw:
            try:
                pred = json.loads(raw)
            except Exception:
                pass
    if not pred:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT anomaly_score, failure_probability, days_to_failure, confidence, predicted_at
                FROM predictions WHERE equipment_id = %s ORDER BY predicted_at DESC LIMIT 1
            """, (eq_int,))
            p_row = cur.fetchone()
            if p_row:
                pred = {
                    "anomaly_score": float(p_row["anomaly_score"] or 0),
                    "failure_probability": float(p_row["failure_probability"] or 0),
                    "days_to_failure": float(p_row["days_to_failure"] or 45),
                    "confidence": float(p_row["confidence"] or 0.94),
                }

    pdf_bytes = generate_equipment_report_pdf(detail=detail, prediction=pred)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Zydus_{detail['equipment_id']}_Reliability_Report.pdf"},
    )


@app.get("/api/ml/drift-status")
def get_ml_drift_status(
    equipment_id: str = "GRAN-LINE-01",
    user: dict = Depends(get_current_user),
):
    """Returns real-time Population Stability Index (PSI) feature drift status."""
    from ml.drift_evaluator import evaluate_dataset_drift
    from ml.retrain_pipeline import fetch_historical_training_data
    from domain.equipment import resolve_equipment_id

    eq_int = resolve_equipment_id(equipment_id)
    baseline = fetch_historical_training_data(eq_int, hours=72)
    current = fetch_historical_training_data(eq_int, hours=24)
    drift = evaluate_dataset_drift(baseline, current)
    
    return {
        "equipment_id": equipment_id,
        "champion_model_version": "v3.0.0-PROD (Ensemble: IsolationForest + LSTM + XGBoost)",
        "regulatory_tier": "GAMP 5 Category 4 / US FDA 21 CFR Part 11",
        "baseline_window_hours": 72,
        "current_window_hours": 24,
        **drift,
    }


@app.post("/api/ml/retrain")
def trigger_ml_retraining(
    payload: dict,
    user: dict = Depends(require_role("admin", "engineer")),
):
    """Triggers autonomous candidate retraining and challenger-champion benchmarking."""
    from ml.retrain_pipeline import execute_retraining_cycle

    eq_id = payload.get("equipment_id", "GRAN-LINE-01")
    force = payload.get("force_promotion", False)
    res = execute_retraining_cycle(equipment_code=eq_id, force_promotion=force)
    return res


@app.post("/api/alerts/test-webhook")
def test_alert_webhook(
    payload: dict,
    user: dict = Depends(require_role("admin", "engineer")),
):
    """Tests multi-channel industrial alert webhook dispatch (Slack/Teams)."""
    from services.notification_service import dispatch_alert_webhook
    return dispatch_alert_webhook(payload)


# ------------------------------------------------------------
#  GLOBAL ERROR HANDLER
# ------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal server error", "code": 500},
    )
