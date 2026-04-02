"""
Kafka Consumer → TimescaleDB
=============================
Consumes sensor readings from Kafka and persists them to TimescaleDB.
Runs as a background thread within the FastAPI process.
"""

import json
import os
import time
import logging
import threading

import psycopg2
import psycopg2.extras
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logger = logging.getLogger("kafka-consumer")

# Batch insert config
BATCH_SIZE = 100
BATCH_TIMEOUT = 2.0  # seconds — flush even if batch isn't full


class SensorDataConsumer:
    """Consumes sensor data from Kafka and writes to TimescaleDB."""

    def __init__(self):
        self.db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
        )
        self.kafka_broker = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = "equipment.sensors.raw"

        self.equipment_map = {}  # name → id
        self.running = False
        self._thread = None

        # Stats
        self._readings_count = 0
        self._last_log_time = time.time()

    # ── Database ────────────────────────────────────────────
    def _get_db_connection(self):
        """Create a new database connection."""
        return psycopg2.connect(self.db_url)

    def _load_equipment_map(self):
        """Load equipment name → id mapping from DB."""
        retries = 0
        while retries < 10:
            try:
                conn = self._get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, name FROM equipment")
                rows = cur.fetchall()
                self.equipment_map = {name: eid for eid, name in rows}
                cur.close()
                conn.close()
                logger.info(f"Loaded {len(self.equipment_map)} equipment mappings")
                return
            except Exception as e:
                retries += 1
                logger.warning(f"DB not ready (attempt {retries}): {e}. Retrying in 3s...")
                time.sleep(3)

        logger.error("Failed to load equipment map after 10 retries")

    # ── Batch Insert ────────────────────────────────────────
    def _insert_batch(self, conn, batch):
        """Insert a batch of readings into sensor_readings."""
        if not batch:
            return 0

        insert_sql = """
            INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, timestamp)
            VALUES %s
        """
        values = []
        for reading in batch:
            eq_name = reading.get("equipment_id")
            eq_id = self.equipment_map.get(eq_name)
            if eq_id is None:
                continue
            values.append((
                eq_id,
                reading["sensor_name"],
                reading["value"],
                reading.get("unit", ""),
                reading["timestamp"],
            ))

        if values:
            cur = conn.cursor()
            psycopg2.extras.execute_values(cur, insert_sql, values, page_size=BATCH_SIZE)
            conn.commit()
            cur.close()

        return len(values)

    # ── Stats Logging ───────────────────────────────────────
    def _log_stats(self):
        """Log throughput every 60 seconds."""
        now = time.time()
        elapsed = now - self._last_log_time
        if elapsed >= 60:
            rate = self._readings_count / elapsed
            logger.info(
                f"[{time.strftime('%H:%M:%S')}] Saved {self._readings_count} readings "
                f"in last {int(elapsed)} seconds ({rate:.0f}/sec)"
            )
            self._readings_count = 0
            self._last_log_time = now

    # ── Consumer Loop ───────────────────────────────────────
    def _consume_loop(self):
        """Main consumption loop with auto-reconnect."""
        self._load_equipment_map()

        while self.running:
            consumer = None
            conn = None
            try:
                logger.info(f"Connecting to Kafka at {self.kafka_broker}...")
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.kafka_broker,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    group_id="zydus-sensor-consumer",
                    consumer_timeout_ms=BATCH_TIMEOUT * 1000,
                )
                logger.info("Kafka consumer connected")

                conn = self._get_db_connection()
                logger.info("Database connection established")

                batch = []
                last_flush = time.time()

                while self.running:
                    # Poll for messages
                    msg_pack = consumer.poll(timeout_ms=int(BATCH_TIMEOUT * 1000))

                    for tp, messages in msg_pack.items():
                        for message in messages:
                            batch.append(message.value)

                    # Flush batch if full or timeout
                    now = time.time()
                    if len(batch) >= BATCH_SIZE or (batch and now - last_flush >= BATCH_TIMEOUT):
                        try:
                            saved = self._insert_batch(conn, batch)
                            self._readings_count += saved
                        except psycopg2.OperationalError:
                            logger.warning("DB connection lost, reconnecting...")
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = self._get_db_connection()
                            saved = self._insert_batch(conn, batch)
                            self._readings_count += saved

                        batch = []
                        last_flush = now

                    self._log_stats()

            except NoBrokersAvailable:
                logger.warning("Kafka not available. Reconnecting in 5s...")
            except Exception as e:
                logger.error(f"Consumer error: {e}. Reconnecting in 5s...")
            finally:
                if consumer:
                    try:
                        consumer.close()
                    except Exception:
                        pass
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

            if self.running:
                time.sleep(5)

    # ── Start/Stop ──────────────────────────────────────────
    def start(self):
        """Start the consumer in a background thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True, name="kafka-consumer")
        self._thread.start()
        logger.info("Kafka consumer thread started")

    def stop(self):
        """Stop the consumer."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Kafka consumer stopped")
