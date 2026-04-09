"""
Alert Engine - Generates alerts and work orders from predictions
=================================================================
Runs every 30 seconds via Celery Beat.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import psycopg2
import redis as redis_lib
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from celery_app import celery_app
from common.reliability import retry_call

logger = logging.getLogger("alert-engine")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KAFKA_BROKER = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

CRITICAL_FAILURE_PROB_THRESHOLD = float(os.environ.get("CRITICAL_FAILURE_PROB_THRESHOLD", "0.80"))
WARNING_FAILURE_PROB_THRESHOLD = float(os.environ.get("WARNING_FAILURE_PROB_THRESHOLD", "0.40"))
CRITICAL_ANOMALY_THRESHOLD = float(os.environ.get("CRITICAL_ANOMALY_THRESHOLD", "0.90"))
WARNING_ANOMALY_THRESHOLD = float(os.environ.get("WARNING_ANOMALY_THRESHOLD", "0.70"))
CRITICAL_DAYS_TO_FAILURE_THRESHOLD = float(os.environ.get("CRITICAL_DAYS_TO_FAILURE_THRESHOLD", "3"))
WARNING_DAYS_TO_FAILURE_THRESHOLD = float(os.environ.get("WARNING_DAYS_TO_FAILURE_THRESHOLD", "14"))
CRITICAL_ALERT_COOLDOWN_HOURS = int(os.environ.get("CRITICAL_ALERT_COOLDOWN_HOURS", "6"))
WARNING_ALERT_COOLDOWN_HOURS = int(os.environ.get("WARNING_ALERT_COOLDOWN_HOURS", "2"))
PREDICTION_STALE_MINUTES = int(os.environ.get("PREDICTION_STALE_MINUTES", "10"))
DB_RETRIES = int(os.environ.get("ALERT_DB_RETRIES", "3"))
REDIS_RETRIES = int(os.environ.get("ALERT_REDIS_RETRIES", "3"))

EQUIPMENT_IDS = [
    "MFG-LINE-01", "MFG-LINE-02", "MFG-LINE-03", "MFG-LINE-04", "MFG-LINE-05",
    "COLD-UNIT-01", "COLD-UNIT-02", "COLD-UNIT-03", "COLD-UNIT-04",
    "LAB-HPLC-01", "LAB-HPLC-02", "LAB-HPLC-03", "LAB-HPLC-04",
    "INF-PUMP-01", "INF-PUMP-02", "INF-PUMP-03", "INF-PUMP-04",
    "RAD-UNIT-01", "RAD-UNIT-02", "RAD-UNIT-03",
]

EVENT_TOPICS = {
    "CRITICAL": "equipment.alerts.critical",
    "WARNING": "equipment.alerts.warning",
}

_redis = None
_producer = None


def get_redis():
    global _redis
    if _redis is not None:
        return _redis

    def connect():
        client = redis_lib.from_url(REDIS_URL)
        client.ping()
        return client

    try:
        _redis = retry_call(
            connect,
            retries=REDIS_RETRIES,
            initial_delay=1.0,
            retry_exceptions=(redis_lib.RedisError,),
            logger=logger,
            operation_name="alert redis connection",
        )
    except redis_lib.RedisError:
        _redis = None
    return _redis


def get_db_connection():
    return retry_call(
        lambda: psycopg2.connect(DB_URL),
        retries=DB_RETRIES,
        initial_delay=1.0,
        retry_exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError),
        logger=logger,
        operation_name="alert database connection",
    )


def get_kafka_producer():
    global _producer
    if _producer is not None:
        return _producer

    try:
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            acks="all",
            retries=5,
            linger_ms=50,
            request_timeout_ms=5000,
            max_block_ms=5000,
        )
    except NoBrokersAvailable:
        logger.warning("Kafka not available for alert publishing")
    return _producer


def get_equipment_map():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM equipment")
            return {name: equipment_id for equipment_id, name in cur.fetchall()}
    finally:
        conn.close()


def parse_prediction_timestamp(prediction: dict) -> datetime | None:
    raw_timestamp = prediction.get("predicted_at")
    if not raw_timestamp:
        return None

    try:
        timestamp = datetime.fromisoformat(raw_timestamp)
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp
    except ValueError:
        logger.debug("Unable to parse predicted_at timestamp: %s", raw_timestamp)
        return None


def is_prediction_stale(prediction: dict) -> bool:
    prediction_ts = parse_prediction_timestamp(prediction)
    if prediction_ts is None:
        return False
    return prediction_ts < datetime.now(timezone.utc) - timedelta(minutes=PREDICTION_STALE_MINUTES)


def build_alert_classification(prediction: dict) -> dict | None:
    fp = float(prediction.get("failure_probability") or 0.0)
    anomaly = float(prediction.get("anomaly_score") or 0.0)
    days_to_failure = float(prediction.get("days_to_failure") or 999.0)

    severity = None
    cooldown_hours = 0
    reasons = []

    if fp >= CRITICAL_FAILURE_PROB_THRESHOLD:
        reasons.append(f"failure probability {fp:.2f}")
    if anomaly >= CRITICAL_ANOMALY_THRESHOLD:
        reasons.append(f"anomaly score {anomaly:.2f}")
    if days_to_failure <= CRITICAL_DAYS_TO_FAILURE_THRESHOLD:
        reasons.append(f"predicted failure in {days_to_failure:.1f} days")

    if reasons:
        severity = "CRITICAL"
        cooldown_hours = CRITICAL_ALERT_COOLDOWN_HOURS
    else:
        if fp >= WARNING_FAILURE_PROB_THRESHOLD:
            reasons.append(f"failure probability {fp:.2f}")
        if anomaly >= WARNING_ANOMALY_THRESHOLD:
            reasons.append(f"anomaly score {anomaly:.2f}")
        if days_to_failure <= WARNING_DAYS_TO_FAILURE_THRESHOLD:
            reasons.append(f"predicted failure in {days_to_failure:.1f} days")
        if reasons:
            severity = "WARNING"
            cooldown_hours = WARNING_ALERT_COOLDOWN_HOURS

    if severity is None:
        return None

    message = (
        f"AI detected {severity.lower()} equipment risk "
        f"({', '.join(reasons)}). "
        + ("Immediate inspection required." if severity == "CRITICAL" else "Monitor closely.")
    )

    return {
        "severity": severity,
        "cooldown_hours": cooldown_hours,
        "message": message,
        "days_to_failure": days_to_failure,
        "failure_probability": fp,
        "anomaly_score": anomaly,
        "create_work_order": severity == "CRITICAL",
    }


def has_recent_alert(conn, equipment_db_id: int, severity: str, cooldown_hours: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM alerts
            WHERE equipment_id = %s
              AND severity = %s
              AND acknowledged_at IS NULL
              AND created_at > NOW() - (%s * INTERVAL '1 hour')
            """,
            (equipment_db_id, severity, cooldown_hours),
        )
        return cur.fetchone()[0] > 0


def has_active_critical_signal(conn, equipment_db_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM alerts
            WHERE equipment_id = %s
              AND severity = 'CRITICAL'
              AND acknowledged_at IS NULL
              AND created_at > NOW() - (%s * INTERVAL '1 hour')
            """,
            (equipment_db_id, CRITICAL_ALERT_COOLDOWN_HOURS),
        )
        active_alerts = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM work_orders
            WHERE equipment_id = %s
              AND priority = 'CRITICAL'
              AND status = 'open'
            """,
            (equipment_db_id,),
        )
        open_work_orders = cur.fetchone()[0]

    return active_alerts > 0 or open_work_orders > 0


def upsert_critical_work_order(conn, equipment_db_id: int, message: str, days_to_failure: float) -> bool:
    predicted_failure_date = (datetime.now(timezone.utc) + timedelta(days=max(days_to_failure, 0.0))).date()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, predicted_failure_date
            FROM work_orders
            WHERE equipment_id = %s
              AND priority = 'CRITICAL'
              AND status = 'open'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (equipment_db_id,),
        )
        row = cur.fetchone()
        if row:
            work_order_id, existing_failure_date = row
            if existing_failure_date is None or predicted_failure_date <= existing_failure_date:
                cur.execute(
                    """
                    UPDATE work_orders
                    SET description = %s,
                        predicted_failure_date = %s
                    WHERE id = %s
                    """,
                    (message, predicted_failure_date, work_order_id),
                )
            return False

        cur.execute(
            """
            INSERT INTO work_orders (
                equipment_id, priority, description, predicted_failure_date, status
            )
            VALUES (%s, 'CRITICAL', %s, %s, 'open')
            """,
            (equipment_db_id, message, predicted_failure_date),
        )
        return True


def publish_alert_event(producer, equipment_id: str, classification: dict) -> None:
    if producer is None:
        return

    payload = {
        "equipment_id": equipment_id,
        "severity": classification["severity"],
        "failure_probability": classification["failure_probability"],
        "anomaly_score": classification["anomaly_score"],
        "days_to_failure": classification["days_to_failure"],
        "message": classification["message"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        producer.send(EVENT_TOPICS[classification["severity"]], value=payload)
    except KafkaError as exc:
        logger.warning("Kafka publish failed for %s: %s", equipment_id, exc)


@celery_app.task(
    name="ml_service.alert_engine.run_alert_engine",
    bind=True,
    autoretry_for=(psycopg2.Error,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def run_alert_engine(self):
    """Evaluate predictions and generate alerts/work orders."""
    redis_client = get_redis()
    if redis_client is None:
        logger.warning("Redis not available - skipping alert cycle")
        return {"status": "skipped", "reason": "redis_unavailable"}

    producer = get_kafka_producer()
    try:
        equipment_map = get_equipment_map()
    except psycopg2.Error as exc:
        logger.error("Cannot load equipment map: %s", exc)
        return {"status": "error", "reason": "equipment_map_unavailable"}

    conn = get_db_connection()
    critical_count = 0
    warning_count = 0
    deduped_count = 0
    stale_count = 0
    suppressed_count = 0
    nominal_count = 0
    ts = time.strftime("%H:%M:%S")

    try:
        for equipment_id in EQUIPMENT_IDS:
            try:
                raw_prediction = redis_client.get(f"pred:{equipment_id}")
                if not raw_prediction:
                    continue

                prediction = json.loads(raw_prediction)
                if is_prediction_stale(prediction):
                    stale_count += 1
                    continue

                equipment_db_id = equipment_map.get(equipment_id)
                if not equipment_db_id:
                    continue

                classification = build_alert_classification(prediction)
                if classification is None:
                    nominal_count += 1
                    continue

                if classification["severity"] == "WARNING" and has_active_critical_signal(conn, equipment_db_id):
                    suppressed_count += 1
                    logger.info("Suppressing warning for %s due to active critical state", equipment_id)
                    continue

                if has_recent_alert(
                    conn,
                    equipment_db_id,
                    classification["severity"],
                    classification["cooldown_hours"],
                ):
                    deduped_count += 1
                    if classification["create_work_order"]:
                        upsert_critical_work_order(
                            conn,
                            equipment_db_id,
                            classification["message"],
                            classification["days_to_failure"],
                        )
                        conn.commit()
                    continue

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO alerts (equipment_id, severity, message)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            equipment_db_id,
                            classification["severity"],
                            classification["message"],
                        ),
                    )

                if classification["create_work_order"]:
                    upsert_critical_work_order(
                        conn,
                        equipment_db_id,
                        classification["message"],
                        classification["days_to_failure"],
                    )
                    critical_count += 1
                else:
                    warning_count += 1

                conn.commit()
                publish_alert_event(producer, equipment_id, classification)

                logger.warning(
                    "[%s] %s - fp=%.2f anomaly=%.2f dtf=%.1f",
                    classification["severity"],
                    equipment_id,
                    classification["failure_probability"],
                    classification["anomaly_score"],
                    classification["days_to_failure"],
                )
            except Exception as exc:
                conn.rollback()
                logger.error("Alert processing failed for %s: %s", equipment_id, exc)
    finally:
        conn.close()
        if producer is not None:
            try:
                producer.flush()
            except KafkaError:
                logger.debug("Kafka flush failed during alert cycle")

    logger.info(
        "[%s] Alerts: %s critical, %s warning, %s deduped, %s suppressed, %s stale, %s nominal",
        ts,
        critical_count,
        warning_count,
        deduped_count,
        suppressed_count,
        stale_count,
        nominal_count,
    )
    return {
        "critical": critical_count,
        "warning": warning_count,
        "deduped": deduped_count,
        "suppressed": suppressed_count,
        "stale": stale_count,
        "nominal": nominal_count,
    }
