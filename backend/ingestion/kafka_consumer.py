"""
Kafka Consumer -> TimescaleDB
=============================
Consumes sensor readings from Kafka and persists them to TimescaleDB.
Runs as a background thread within the FastAPI process.
"""

import json
import logging
import os
import threading
import time

import psycopg2
import psycopg2.extras
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from common.reliability import retry_call

logger = logging.getLogger("kafka-consumer")

BATCH_SIZE = 100
BATCH_TIMEOUT = 2.0
DB_RETRIES = int(os.environ.get("INGEST_DB_RETRIES", "3"))


class SensorDataConsumer:
    """Consumes sensor data from Kafka and writes to TimescaleDB."""

    def __init__(self):
        self.db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
        )
        self.kafka_broker = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = "equipment.sensors.raw"

        self.equipment_map = {}
        self.running = False
        self._thread = None

        self._readings_count = 0
        self._last_log_time = time.time()

    def _get_db_connection(self):
        return retry_call(
            lambda: psycopg2.connect(self.db_url),
            retries=DB_RETRIES,
            initial_delay=1.0,
            retry_exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError),
            logger=logger,
            operation_name="ingestion database connection",
        )

    def _load_equipment_map(self):
        retries = 0
        while retries < 10:
            try:
                conn = self._get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, name FROM equipment")
                        self.equipment_map = {name: equipment_id for equipment_id, name in cur.fetchall()}
                finally:
                    conn.close()
                logger.info("Loaded %s equipment mappings", len(self.equipment_map))
                return
            except Exception as exc:
                retries += 1
                logger.warning("DB not ready (attempt %s): %s. Retrying in 3s...", retries, exc)
                time.sleep(3)

        logger.error("Failed to load equipment map after 10 retries")

    def _insert_batch(self, conn, batch):
        """Insert a batch of readings into sensor_readings."""
        if not batch:
            return 0

        values = []
        for reading in batch:
            equipment_name = reading.get("equipment_id")
            equipment_id = self.equipment_map.get(equipment_name)
            if equipment_id is None:
                logger.debug("Skipping reading with unknown equipment id %s", equipment_name)
                continue

            required_keys = {"sensor_name", "value", "timestamp"}
            if not required_keys.issubset(reading):
                logger.debug("Skipping malformed reading payload: %s", reading)
                continue

            values.append(
                (
                    equipment_id,
                    reading["sensor_name"],
                    reading["value"],
                    reading.get("unit", ""),
                    reading["timestamp"],
                )
            )

        if not values:
            return 0

        insert_sql = """
            INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, timestamp)
            VALUES %s
        """

        with conn.cursor() as cur:
            try:
                psycopg2.extras.execute_values(cur, insert_sql, values, page_size=BATCH_SIZE)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return len(values)

    def _log_stats(self):
        now = time.time()
        elapsed = now - self._last_log_time
        if elapsed >= 60:
            rate = self._readings_count / elapsed
            logger.info(
                "[%s] Saved %s readings in last %s seconds (%.0f/sec)",
                time.strftime("%H:%M:%S"),
                self._readings_count,
                int(elapsed),
                rate,
            )
            self._readings_count = 0
            self._last_log_time = now

    def _consume_loop(self):
        self._load_equipment_map()

        while self.running:
            consumer = None
            conn = None
            try:
                logger.info("Connecting to Kafka at %s...", self.kafka_broker)
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.kafka_broker,
                    value_deserializer=lambda msg: json.loads(msg.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    group_id="zydus-sensor-consumer",
                    consumer_timeout_ms=int(BATCH_TIMEOUT * 1000),
                )
                logger.info("Kafka consumer connected")

                conn = self._get_db_connection()
                logger.info("Database connection established")

                batch = []
                last_flush = time.time()

                while self.running:
                    msg_pack = consumer.poll(timeout_ms=int(BATCH_TIMEOUT * 1000))
                    for _, messages in msg_pack.items():
                        for message in messages:
                            batch.append(message.value)

                    now = time.time()
                    if len(batch) >= BATCH_SIZE or (batch and now - last_flush >= BATCH_TIMEOUT):
                        try:
                            saved = self._insert_batch(conn, batch)
                            self._readings_count += saved
                        except psycopg2.Error:
                            logger.warning("DB write failed, reconnecting and retrying batch...")
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
            except Exception as exc:
                logger.error("Consumer error: %s. Reconnecting in 5s...", exc)
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

    def start(self):
        """Start the consumer in a background thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._consume_loop,
            daemon=True,
            name="kafka-consumer",
        )
        self._thread.start()
        logger.info("Kafka consumer thread started")

    def stop(self):
        """Stop the consumer."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Kafka consumer stopped")
