"""
WebSocket Live Data Feed
==========================
Pushes real-time sensor data & alerts to connected clients.
"""

import os
import json
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import psycopg2
import psycopg2.extras
import redis as redis_lib

logger = logging.getLogger("websocket")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

IDLE_TIMEOUT = 600  # 10 minutes
MAX_CONNECTIONS = 50

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections with idle timeout."""

    def __init__(self):
        self.active_connections: dict[WebSocket, float] = {}

    async def connect(self, ws: WebSocket):
        if len(self.active_connections) >= MAX_CONNECTIONS:
            await ws.close(code=1013, reason="Max connections reached")
            return False
        await ws.accept()
        self.active_connections[ws] = time.time()
        logger.info(f"WS connected ({len(self.active_connections)} active)")
        return True

    def disconnect(self, ws: WebSocket):
        self.active_connections.pop(ws, None)
        logger.info(f"WS disconnected ({len(self.active_connections)} active)")

    def touch(self, ws: WebSocket):
        self.active_connections[ws] = time.time()

    async def broadcast(self, message: dict):
        stale = []
        for ws, last_active in list(self.active_connections.items()):
            if time.time() - last_active > IDLE_TIMEOUT:
                stale.append(ws)
                continue
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.active_connections.pop(ws, None)
            try:
                await ws.close(code=1000, reason="Idle timeout")
            except Exception:
                pass


manager = ConnectionManager()


EQUIPMENT_IDS = [
    "MFG-LINE-01", "MFG-LINE-02", "MFG-LINE-03", "MFG-LINE-04", "MFG-LINE-05",
    "COLD-UNIT-01", "COLD-UNIT-02", "COLD-UNIT-03", "COLD-UNIT-04",
    "LAB-HPLC-01", "LAB-HPLC-02", "LAB-HPLC-03", "LAB-HPLC-04",
    "INF-PUMP-01", "INF-PUMP-02", "INF-PUMP-03", "INF-PUMP-04",
    "RAD-UNIT-01", "RAD-UNIT-02", "RAD-UNIT-03",
]


def get_equipment_summary():
    """Fetch current status of all equipment from Redis predictions."""
    try:
        r = redis_lib.from_url(REDIS_URL)
        summaries = []
        for eq_id in EQUIPMENT_IDS:
            raw = r.get(f"pred:{eq_id}")
            if raw:
                pred = json.loads(raw)
                fp = pred.get("failure_probability", 0)
                health = "critical" if fp > 0.80 else "warning" if fp > 0.40 else "healthy"
                summaries.append({
                    "equipment_id": eq_id,
                    "health_status": health,
                    "anomaly_score": pred.get("anomaly_score", 0),
                    "failure_probability": fp,
                    "days_to_failure": pred.get("days_to_failure", 999),
                })
            else:
                summaries.append({"equipment_id": eq_id, "health_status": "unknown",
                                  "anomaly_score": 0, "failure_probability": 0,
                                  "days_to_failure": 999})
        return summaries
    except Exception as e:
        logger.error(f"Redis summary error: {e}")
        return []


def get_latest_sensor_batch():
    """Fetch the most recent sensor readings for all equipment."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT e.name as equipment_id, sr.sensor_name, sr.value, sr.unit,
                   sr.timestamp AT TIME ZONE 'UTC' as timestamp
            FROM sensor_readings sr
            JOIN equipment e ON sr.equipment_id = e.id
            WHERE sr.timestamp > NOW() - INTERVAL '10 seconds'
            ORDER BY sr.timestamp DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{
            "equipment_id": r["equipment_id"],
            "sensor_name": r["sensor_name"],
            "value": round(r["value"], 4),
            "unit": r["unit"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
        } for r in rows]
    except Exception as e:
        logger.error(f"Sensor batch error: {e}")
        return []


def get_recent_alerts(seconds=30):
    """Fetch alerts created in the last N seconds."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.id, e.name as equipment_id, a.severity, a.message,
                   a.created_at AT TIME ZONE 'UTC' as created_at
            FROM alerts a
            JOIN equipment e ON a.equipment_id = e.id
            WHERE a.created_at > NOW() - INTERVAL '%s seconds'
            ORDER BY a.created_at DESC
        """, (seconds,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{
            "id": r["id"],
            "equipment_id": r["equipment_id"],
            "severity": r["severity"],
            "message": r["message"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        } for r in rows]
    except Exception as e:
        logger.error(f"Alert fetch error: {e}")
        return []


@router.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    connected = await manager.connect(ws)
    if not connected:
        return

    try:
        # Send initial summary on connect
        summary = get_equipment_summary()
        await ws.send_json({"type": "initial_summary", "data": summary})

        last_alert_check = time.time()

        while True:
            # Send sensor batch every 5 seconds
            sensor_data = get_latest_sensor_batch()
            if sensor_data:
                await ws.send_json({"type": "sensor_update", "data": sensor_data})

            # Check for new alerts
            now = time.time()
            elapsed = now - last_alert_check
            alerts = get_recent_alerts(seconds=max(5, int(elapsed)))
            last_alert_check = now
            for alert in alerts:
                alert_type = "critical_alert" if alert["severity"] == "CRITICAL" else "warning_alert"
                await ws.send_json({"type": alert_type, "data": alert})

            manager.touch(ws)

            # Listen for client pings (keeps connection alive)
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=5.0)
                manager.touch(ws)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        manager.disconnect(ws)
