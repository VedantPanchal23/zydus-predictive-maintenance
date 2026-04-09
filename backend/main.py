"""
Zydus Pharma Oncology — Predictive Maintenance API
=====================================================
Complete REST API + WebSocket for the frontend.
"""

import os
import json
import logging
import math
import threading
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import psycopg2
import psycopg2.extras
import redis as redis_lib

from auth.auth import router as auth_router, get_current_user, require_role
from websocket.live import router as ws_router

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zydus-backend")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# ── Kafka consumer instance ─────────────────────────────────
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


# ── Lifespan ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Zydus Predictive Maintenance Backend...")
    kafka_thread = threading.Thread(target=_startup_kafka, daemon=True, name="kafka-setup")
    kafka_thread.start()
    logger.info("Backend is ready")
    yield
    logger.info("Shutting down...")
    if _consumer:
        _consumer.stop()


# ── FastAPI App ─────────────────────────────────────────────
app = FastAPI(
    title="Zydus Predictive Maintenance API",
    description="AI-powered predictive maintenance for Zydus Pharma Oncology equipment",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(ws_router)


# ── DB & Redis helpers ──────────────────────────────────────
def get_db():
    return psycopg2.connect(DB_URL)


def get_redis():
    try:
        r = redis_lib.from_url(REDIS_URL)
        r.ping()
        return r
    except Exception:
        return None


def error_response(code: int, message: str):
    raise HTTPException(status_code=code, detail={"error": True, "message": message, "code": code})


# ── Pydantic Schemas ────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    limit: int
    pages: int


# ════════════════════════════════════════════════════════════
#  PUBLIC ENDPOINTS (no auth)
# ════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "service": "zydus-backend"}


@app.get("/")
def root():
    return {"message": "Zydus Pharma Oncology - Predictive Maintenance System"}


# ════════════════════════════════════════════════════════════
#  EQUIPMENT ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/api/equipment")
def list_equipment(user: dict = Depends(get_current_user)):
    """List all 20 equipment with current health status."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM equipment ORDER BY id")
    equipments = cur.fetchall()
    cur.close()
    conn.close()

    r = get_redis()
    result = []
    for eq in equipments:
        health = "unknown"
        if r:
            raw = r.get(f"pred:{eq['name']}")
            if raw:
                pred = json.loads(raw)
                fp = pred.get("failure_probability", 0)
                health = "critical" if fp > 0.80 else "warning" if fp > 0.40 else "healthy"

        result.append({
            "id": eq["id"],
            "name": eq["name"],
            "type": eq["type"],
            "location": eq["location"],
            "install_date": eq["install_date"].isoformat() if eq["install_date"] else None,
            "last_maintenance_date": eq["last_maintenance_date"].isoformat() if eq["last_maintenance_date"] else None,
            "status": eq["status"],
            "current_health": health,
        })
    return result


@app.get("/api/equipment/{equipment_id}")
def get_equipment(equipment_id: int, user: dict = Depends(get_current_user)):
    """Single equipment with full detail + latest prediction + open alerts count."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM equipment WHERE id = %s", (equipment_id,))
    eq = cur.fetchone()
    if not eq:
        cur.close(); conn.close()
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
    cur.close()
    conn.close()

    prediction = None
    health = "unknown"
    if pred_row:
        fp = pred_row["failure_probability"] or 0
        health = "critical" if fp > 0.80 else "warning" if fp > 0.40 else "healthy"
        prediction = {
            "anomaly_score": round(float(pred_row["anomaly_score"] or 0), 4),
            "failure_probability": round(float(fp), 4),
            "days_to_failure": round(float(pred_row["days_to_failure"] or 999), 1),
            "confidence": round(float(pred_row["confidence"] or 0), 4),
            "predicted_at": pred_row["predicted_at"].isoformat() if pred_row["predicted_at"] else None,
        }

    return {
        "id": eq["id"],
        "name": eq["name"],
        "type": eq["type"],
        "location": eq["location"],
        "install_date": eq["install_date"].isoformat() if eq["install_date"] else None,
        "last_maintenance_date": eq["last_maintenance_date"].isoformat() if eq["last_maintenance_date"] else None,
        "status": eq["status"],
        "current_health": health,
        "latest_prediction": prediction,
        "open_alerts_count": alert_count,
    }


@app.get("/api/equipment/{equipment_id}/sensors")
def get_equipment_sensors(equipment_id: int, user: dict = Depends(get_current_user)):
    """Last 24 hours of sensor readings grouped by sensor_name."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify equipment exists
    cur.execute("SELECT id FROM equipment WHERE id = %s", (equipment_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        error_response(404, f"Equipment {equipment_id} not found")

    cur.execute("""
        SELECT sensor_name, value, unit, timestamp AT TIME ZONE 'UTC' as timestamp
        FROM sensor_readings
        WHERE equipment_id = %s AND timestamp > NOW() - INTERVAL '24 hours'
        ORDER BY timestamp ASC
    """, (equipment_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

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
    """Latest prediction from Redis (fast), falls back to DB."""
    # Get equipment name for Redis key
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT name FROM equipment WHERE id = %s", (equipment_id,))
    eq = cur.fetchone()
    if not eq:
        cur.close(); conn.close()
        error_response(404, f"Equipment {equipment_id} not found")

    # Try Redis first
    r = get_redis()
    if r:
        raw = r.get(f"pred:{eq['name']}")
        if raw:
            cur.close(); conn.close()
            return json.loads(raw)

    # Fallback to DB
    cur.execute("""
        SELECT anomaly_score, failure_probability, days_to_failure,
               confidence, predicted_at
        FROM predictions WHERE equipment_id = %s ORDER BY predicted_at DESC LIMIT 1
    """, (equipment_id,))
    pred = cur.fetchone()
    cur.close()
    conn.close()

    if not pred:
        return {"message": "No predictions available yet"}

    return {
        "equipment_id": eq["name"],
        "anomaly_score": round(float(pred["anomaly_score"] or 0), 4),
        "failure_probability": round(float(pred["failure_probability"] or 0), 4),
        "days_to_failure": round(float(pred["days_to_failure"] or 999), 1),
        "confidence": round(float(pred["confidence"] or 0), 4),
        "model_version": "v1",
        "predicted_at": pred["predicted_at"].isoformat() if pred["predicted_at"] else None,
    }


@app.get("/api/equipment/{equipment_id}/history")
def get_equipment_prediction_history(equipment_id: int, user: dict = Depends(get_current_user)):
    """Last 30 predictions for trend chart."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM equipment WHERE id = %s", (equipment_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        error_response(404, f"Equipment {equipment_id} not found")

    cur.execute("""
        SELECT anomaly_score, failure_probability, days_to_failure,
               confidence, predicted_at
        FROM predictions WHERE equipment_id = %s
        ORDER BY predicted_at DESC LIMIT 30
    """, (equipment_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "anomaly_score": round(float(r["anomaly_score"] or 0), 4),
        "failure_probability": round(float(r["failure_probability"] or 0), 4),
        "days_to_failure": round(float(r["days_to_failure"] or 999), 1),
        "confidence": round(float(r["confidence"] or 0), 4),
        "predicted_at": r["predicted_at"].isoformat() if r["predicted_at"] else None,
    } for r in rows]


# ════════════════════════════════════════════════════════════
#  ALERTS ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/api/alerts")
def list_alerts(
    severity: str = Query("ALL", description="CRITICAL, WARNING, or ALL"),
    status: str = Query("open", description="open, acknowledged, or ALL"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """List alerts with filtering and pagination."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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

    # Count
    cur.execute(f"SELECT COUNT(*) as cnt FROM alerts a {where}", params)
    total = cur.fetchone()["cnt"]

    # Fetch
    cur.execute(f"""
        SELECT a.id, e.id as equipment_id, e.name as equipment_name, a.severity, a.message,
               a.created_at AT TIME ZONE 'UTC' as created_at,
               a.acknowledged_at AT TIME ZONE 'UTC' as acknowledged_at
        FROM alerts a JOIN equipment e ON a.equipment_id = e.id
        {where}
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    rows = cur.fetchall()
    cur.close()
    conn.close()

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
def acknowledge_alert(alert_id: int, user: dict = Depends(require_role("admin", "engineer"))):
    """Mark an alert as acknowledged."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM alerts WHERE id = %s", (alert_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        error_response(404, f"Alert {alert_id} not found")

    cur.execute("""
        UPDATE alerts SET acknowledged_at = NOW()
        WHERE id = %s
        RETURNING id, severity, message,
                  created_at AT TIME ZONE 'UTC' as created_at,
                  acknowledged_at AT TIME ZONE 'UTC' as acknowledged_at
    """, (alert_id,))
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": updated["id"],
        "severity": updated["severity"],
        "message": updated["message"],
        "created_at": updated["created_at"].isoformat() if updated["created_at"] else None,
        "acknowledged_at": updated["acknowledged_at"].isoformat() if updated["acknowledged_at"] else None,
    }


# ════════════════════════════════════════════════════════════
#  WORK ORDERS ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/api/workorders")
def list_workorders(
    status: str = Query("open", description="open, in_progress, completed, or ALL"),
    user: dict = Depends(get_current_user),
):
    """List work orders with status filter."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    where = ""
    params = []
    if status.lower() != "all":
        where = "WHERE wo.status = %s"
        params = [status.lower()]

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
    """, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

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
def complete_workorder(workorder_id: int, user: dict = Depends(require_role("admin", "engineer"))):
    """Mark a work order as completed."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM work_orders WHERE id = %s", (workorder_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        error_response(404, f"Work order {workorder_id} not found")

    cur.execute("""
        UPDATE work_orders SET status = 'completed', completed_at = NOW()
        WHERE id = %s
        RETURNING id, priority, description, status,
                  created_at AT TIME ZONE 'UTC' as created_at,
                  completed_at AT TIME ZONE 'UTC' as completed_at
    """, (workorder_id,))
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": updated["id"],
        "priority": updated["priority"],
        "description": updated["description"],
        "status": updated["status"],
        "created_at": updated["created_at"].isoformat() if updated["created_at"] else None,
        "completed_at": updated["completed_at"].isoformat() if updated["completed_at"] else None,
    }


# ════════════════════════════════════════════════════════════
#  LOGS
# ════════════════════════════════════════════════════════════

@app.get("/api/logs")
def list_logs(
    event_type: str = Query("ALL", description="sensor, prediction, alert, workorder, or ALL"),
    limit: int = Query(50, ge=10, le=200),
    user: dict = Depends(get_current_user),
):
    """Combined operational feed for the frontend logs page."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    normalized_type = event_type.lower()
    per_source_limit = max(10, min(limit, 100))
    items = []

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

    cur.close()
    conn.close()

    items.sort(key=lambda item: item["timestamp"] or "", reverse=True)
    items = items[:limit]

    return {
        "items": items,
        "total": len(items),
        "limit": limit,
    }


# ════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════

@app.get("/api/dashboard/summary")
def dashboard_summary(user: dict = Depends(get_current_user)):
    """Dashboard KPI summary."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT COUNT(*) as cnt FROM equipment")
    total_equipment = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM alerts WHERE acknowledged_at IS NULL")
    open_alerts = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM alerts WHERE severity = 'CRITICAL' AND acknowledged_at IS NULL")
    critical_alerts = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM work_orders WHERE status = 'open'")
    open_workorders = cur.fetchone()["cnt"]

    cur.close()
    conn.close()

    # Compute health counts from Redis predictions
    r = get_redis()
    healthy = warning = critical = 0
    scores = []
    equipment_ids = [
        "MFG-LINE-01", "MFG-LINE-02", "MFG-LINE-03", "MFG-LINE-04", "MFG-LINE-05",
        "COLD-UNIT-01", "COLD-UNIT-02", "COLD-UNIT-03", "COLD-UNIT-04",
        "LAB-HPLC-01", "LAB-HPLC-02", "LAB-HPLC-03", "LAB-HPLC-04",
        "INF-PUMP-01", "INF-PUMP-02", "INF-PUMP-03", "INF-PUMP-04",
        "RAD-UNIT-01", "RAD-UNIT-02", "RAD-UNIT-03",
    ]
    for eq_id in equipment_ids:
        if r:
            raw = r.get(f"pred:{eq_id}")
            if raw:
                pred = json.loads(raw)
                fp = pred.get("failure_probability", 0)
                scores.append(1 - fp)  # health score = 1 - failure prob
                if fp > 0.80:
                    critical += 1
                elif fp > 0.40:
                    warning += 1
                else:
                    healthy += 1
                continue
        healthy += 1  # default if no prediction

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


# ════════════════════════════════════════════════════════════
#  GLOBAL ERROR HANDLER
# ════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal server error", "code": 500},
    )
