"""
WebSocket Real-Time Data Broadcaster
====================================
High-performance decoupled broadcast service pushing live sensor telemetry and alerts.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis as redis_lib
import psycopg2.extras

from common.db_pool import get_db_cursor
from common.equipment_registry import list_active_equipment_ids

logger = logging.getLogger("websocket")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
IDLE_TIMEOUT = 600  # 10 minutes
MAX_CONNECTIONS = 50

router = APIRouter()


class ConnectionManager:
    """Thread-safe connection manager with idle timeout and broadcast dispatch."""

    def __init__(self):
        self.active_connections: dict[WebSocket, float] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> bool:
        async with self._lock:
            if len(self.active_connections) >= MAX_CONNECTIONS:
                await ws.close(code=1013, reason="Max connections reached")
                return False
            await ws.accept()
            self.active_connections[ws] = time.time()
            logger.info("WebSocket client connected (%s active)", len(self.active_connections))
            return True

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active_connections.pop(ws, None)
            logger.info("WebSocket client disconnected (%s active)", len(self.active_connections))

    def touch(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections[ws] = time.time()

    async def broadcast(self, message: dict[str, Any]):
        if not self.active_connections:
            return

        stale: list[WebSocket] = []
        now = time.time()

        for ws, last_active in list(self.active_connections.items()):
            if now - last_active > IDLE_TIMEOUT:
                stale.append(ws)
                continue
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self.active_connections.pop(ws, None)
                    try:
                        await ws.close(code=1000, reason="Stale connection")
                    except Exception:
                        pass


manager = ConnectionManager()
_broadcaster_task: asyncio.Task | None = None


def get_equipment_summary() -> list[dict[str, Any]]:
    """Fetch current status of all equipment from Redis predictions."""
    try:
        r = redis_lib.from_url(REDIS_URL)
        summaries = []
        equipment_ids = list_active_equipment_ids()
        for eq_id in equipment_ids:
            raw = r.get(f"pred:{eq_id}")
            if raw:
                pred = json.loads(raw)
                fp = float(pred.get("failure_probability", 0) or 0)
                health = "critical" if fp > 0.80 else "warning" if fp > 0.40 else "healthy"
                summaries.append({
                    "equipment_id": eq_id,
                    "health_status": health,
                    "anomaly_score": round(float(pred.get("anomaly_score", 0) or 0), 4),
                    "failure_probability": round(fp, 4),
                    "days_to_failure": round(float(pred.get("days_to_failure", 999) or 999), 1),
                })
            else:
                summaries.append({
                    "equipment_id": eq_id,
                    "health_status": "unknown",
                    "anomaly_score": 0.0,
                    "failure_probability": 0.0,
                    "days_to_failure": 999.0,
                })
        return summaries
    except Exception as e:
        logger.debug("Redis summary lookup error: %s", e)
        return []


def get_latest_sensor_batch() -> list[dict[str, Any]]:
    """Fetch recent sensor readings across all equipment using connection pool."""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT e.name as equipment_id, sr.sensor_name, sr.value, sr.unit,
                       sr.timestamp AT TIME ZONE 'UTC' as timestamp
                FROM sensor_readings sr
                JOIN equipment e ON sr.equipment_id = e.id
                WHERE sr.timestamp > NOW() - INTERVAL '15 seconds'
                ORDER BY sr.timestamp DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            return [{
                "equipment_id": r["equipment_id"],
                "sensor_name": r["sensor_name"],
                "value": round(float(r["value"]), 4),
                "unit": r["unit"],
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            } for r in rows]
    except Exception as e:
        logger.debug("Sensor batch query error: %s", e)
        return []


def get_recent_alerts(seconds: int = 10) -> list[dict[str, Any]]:
    """Fetch new alerts created in the last N seconds."""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT a.id, e.name as equipment_id, a.severity, a.message,
                       a.created_at AT TIME ZONE 'UTC' as created_at
                FROM alerts a
                JOIN equipment e ON a.equipment_id = e.id
                WHERE a.created_at > NOW() - (%s * INTERVAL '1 second')
                ORDER BY a.created_at DESC
                LIMIT 10
            """, (seconds,))
            rows = cur.fetchall()
            return [{
                "id": r["id"],
                "equipment_id": r["equipment_id"],
                "severity": r["severity"],
                "message": r["message"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            } for r in rows]
    except Exception as e:
        logger.debug("Alert fetch query error: %s", e)
        return []


async def broadcaster_loop():
    """Decoupled single background worker polling database and broadcasting to all WebSockets."""
    logger.info("Started central WebSocket broadcaster background loop")
    last_alert_check = time.time()

    while True:
        try:
            await asyncio.sleep(5.0)
            if not manager.active_connections:
                continue

            # 1. Broadcast live sensor telemetry batch
            sensor_data = get_latest_sensor_batch()
            if sensor_data:
                await manager.broadcast({"type": "sensor_update", "data": sensor_data})

            # 2. Check and broadcast any new alerts
            now = time.time()
            elapsed = now - last_alert_check
            alerts = get_recent_alerts(seconds=max(5, int(elapsed)))
            last_alert_check = now

            for alert in alerts:
                alert_type = "critical_alert" if alert["severity"] == "CRITICAL" else "warning_alert"
                await manager.broadcast({"type": alert_type, "data": alert})

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.debug("Broadcaster loop error: %s", exc)


def start_broadcaster(app=None):
    global _broadcaster_task
    if _broadcaster_task is None or _broadcaster_task.done():
        _broadcaster_task = asyncio.create_task(broadcaster_loop(), name="ws-broadcaster")


def stop_broadcaster():
    global _broadcaster_task
    if _broadcaster_task and not _broadcaster_task.done():
        _broadcaster_task.cancel()


@router.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    connected = await manager.connect(ws)
    if not connected:
        return

    try:
        # Push initial snapshot upon connection
        summary = get_equipment_summary()
        await ws.send_json({"type": "initial_summary", "data": summary})

        # Client event loop (keeps connection open and processes heartbeat pings)
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                manager.touch(ws)
                if msg == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                manager.touch(ws)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error for client: %s", e)
    finally:
        await manager.disconnect(ws)
