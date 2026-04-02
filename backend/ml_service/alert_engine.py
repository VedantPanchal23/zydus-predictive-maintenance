"""
Alert Engine — Generates alerts and work orders from predictions
=================================================================
Runs every 30 seconds via Celery Beat.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone, timedelta

import psycopg2
import redis as redis_lib
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from celery_app import celery_app

logger = logging.getLogger("alert-engine")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BROKER = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

EQUIPMENT_IDS = [
    "MFG-LINE-01", "MFG-LINE-02", "MFG-LINE-03", "MFG-LINE-04", "MFG-LINE-05",
    "COLD-UNIT-01", "COLD-UNIT-02", "COLD-UNIT-03", "COLD-UNIT-04",
    "LAB-HPLC-01", "LAB-HPLC-02", "LAB-HPLC-03", "LAB-HPLC-04",
    "INF-PUMP-01", "INF-PUMP-02", "INF-PUMP-03", "INF-PUMP-04",
    "RAD-UNIT-01", "RAD-UNIT-02", "RAD-UNIT-03",
]

_redis = None
_producer = None


def get_redis():
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL)
            _redis.ping()
        except Exception:
            _redis = None
    return _redis


def get_kafka_producer():
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except NoBrokersAvailable:
            logger.warning("Kafka not available for alert publishing")
    return _producer


def get_equipment_map():
    """Equipment name → DB id mapping."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM equipment")
    mapping = {name: eid for eid, name in cur.fetchall()}
    cur.close()
    conn.close()
    return mapping


def has_recent_critical(conn, eq_db_id, hours=6):
    """Check if a CRITICAL alert exists for this equipment in the last N hours."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM alerts
        WHERE equipment_id = %s AND severity = 'CRITICAL'
        AND created_at > NOW() - INTERVAL '%s hours'
    """, (eq_db_id, hours))
    count = cur.fetchone()[0]
    cur.close()
    return count > 0


@celery_app.task(name="ml_service.alert_engine.run_alert_engine")
def run_alert_engine():
    """Evaluate predictions and generate alerts/work orders."""
    r = get_redis()
    if r is None:
        logger.warning("Redis not available — skipping alert cycle")
        return {"status": "skipped"}

    producer = get_kafka_producer()
    try:
        eq_map = get_equipment_map()
    except Exception as e:
        logger.error(f"Cannot load equipment map: {e}")
        return {"status": "error"}

    conn = psycopg2.connect(DB_URL)
    critical_count = 0
    warning_count = 0
    nominal_count = 0
    ts = time.strftime("%H:%M:%S")

    for eq_id in EQUIPMENT_IDS:
        try:
            raw = r.get(f"pred:{eq_id}")
            if not raw:
                continue
            pred = json.loads(raw)
            eq_db_id = eq_map.get(eq_id)
            if not eq_db_id:
                continue

            fp = pred.get("failure_probability", 0)
            anomaly = pred.get("anomaly_score", 0)
            dtf = pred.get("days_to_failure", 999)

            # ── CRITICAL ────────────────────────────────────
            if fp > 0.80 or anomaly > 0.90:
                if not has_recent_critical(conn, eq_db_id):
                    cur = conn.cursor()
                    msg = (f"AI predicted failure in {dtf:.1f} days. "
                           f"Anomaly score: {anomaly:.2f}. "
                           f"Immediate inspection required.")
                    cur.execute("""
                        INSERT INTO alerts (equipment_id, severity, message)
                        VALUES (%s, 'CRITICAL', %s)
                    """, (eq_db_id, msg))
                    failure_date = (datetime.now() + timedelta(days=dtf)).date()
                    cur.execute("""
                        INSERT INTO work_orders (equipment_id, priority, description,
                                                 predicted_failure_date, status)
                        VALUES (%s, 'CRITICAL', %s, %s, 'open')
                    """, (eq_db_id, msg, failure_date))
                    conn.commit()
                    cur.close()

                    if producer:
                        producer.send("equipment.alerts.critical", value={
                            "equipment_id": eq_id, "severity": "CRITICAL",
                            "failure_probability": fp, "anomaly_score": anomaly,
                            "days_to_failure": dtf, "message": msg,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    critical_count += 1
                    logger.warning(f"[CRITICAL] {eq_id} — prob={fp:.2f} anomaly={anomaly:.2f}")

            # ── WARNING ─────────────────────────────────────
            elif fp > 0.40:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO alerts (equipment_id, severity, message)
                    VALUES (%s, 'WARNING', %s)
                """, (eq_db_id, f"Elevated failure risk: {fp:.2f}. Monitor closely."))
                conn.commit()
                cur.close()

                if producer:
                    producer.send("equipment.alerts.warning", value={
                        "equipment_id": eq_id, "severity": "WARNING",
                        "failure_probability": fp, "anomaly_score": anomaly,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                warning_count += 1

            # ── NOMINAL ─────────────────────────────────────
            else:
                nominal_count += 1
                logger.debug(f"[OK] {eq_id} nominal (prob={fp:.2f})")

        except Exception as e:
            logger.error(f"Alert error for {eq_id}: {e}")

    conn.close()
    if producer:
        try:
            producer.flush()
        except Exception:
            pass

    logger.info(f"[{ts}] Alerts: {critical_count} critical, {warning_count} warning, {nominal_count} nominal")
    return {"critical": critical_count, "warning": warning_count, "nominal": nominal_count}
