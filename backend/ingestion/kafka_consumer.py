"""
Kafka Telemetry Ingestion Consumer
==================================
High-throughput batch consumer that validates raw sensor readings,
routes corrupt records to the Dead Letter Queue, and micro-batches valid
readings into TimescaleDB.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import psycopg2.extras
from kafka import KafkaConsumer

from core.db_pool import get_db_cursor
from core.metrics import metrics
from domain.telemetry import RawSensorReading
from ingestion.validator import validate_sensor_reading
from ingestion.dlq import record_to_dlq
from domain.equipment import resolve_equipment_id

logger = logging.getLogger("kafka-consumer")

KAFKA_BROKER = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092" if os.name != "nt" else "localhost:9092")
TOPIC_NAME = "equipment.sensors.raw"
BATCH_SIZE = 200
BATCH_TIMEOUT_SEC = 0.5


class SensorDataConsumer:
    def __init__(self, bootstrap_servers: str = KAFKA_BROKER, topic: str = TOPIC_NAME):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.running = False
        self.thread: threading.Thread | None = None
        self._consumer: KafkaConsumer | None = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="kafka-consumer-worker")
        self.thread.start()
        logger.info("Kafka consumer thread started on topic '%s' (broker=%s)", self.topic, self.bootstrap_servers)

    def stop(self):
        self.running = False
        if self._consumer:
            try:
                self._consumer.close(timeout=2.0)
            except Exception:
                pass
        logger.info("Kafka consumer thread stopped")

    def _connect_consumer(self) -> KafkaConsumer:
        while self.running:
            try:
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    group_id="zydus-sensor-ingestion-group",
                    consumer_timeout_ms=1000,
                )
                logger.info("Connected successfully to Kafka broker: %s", self.bootstrap_servers)
                return consumer
            except Exception as exc:
                logger.warning("Kafka broker connection failed (%s). Retrying in 3s...", exc)
                time.sleep(3.0)
        raise RuntimeError("Kafka consumer stopped before connecting")

    def _flush_batch(self, batch: List[Dict[str, Any]]):
        if not batch:
            return
        try:
            records = []
            for r in batch:
                eq_id_int = resolve_equipment_id(r["equipment_id"])
                if eq_id_int is not None:
                    records.append(
                        (
                            eq_id_int,
                            r["sensor_name"],
                            r["value"],
                            r.get("unit"),
                            r["timestamp"],
                        )
                    )
            if not records:
                return

            with get_db_cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, timestamp)
                    VALUES %s;
                    """,
                    records,
                )
            metrics.inc_ingest(len(records))
            logger.debug("Flushed %s sensor readings to TimescaleDB", len(records))
        except Exception as exc:
            logger.error("Failed to insert telemetry batch into TimescaleDB: %s", exc)

    def _run_loop(self):
        self._consumer = self._connect_consumer()
        buffer: List[Dict[str, Any]] = []
        last_flush = time.time()

        while self.running:
            try:
                msg_pack = self._consumer.poll(timeout_ms=500, max_records=BATCH_SIZE)
                for tp, messages in msg_pack.items():
                    for msg in messages:
                        data = msg.value
                        try:
                            reading = RawSensorReading(**data)
                            is_valid, err = validate_sensor_reading(reading)
                            if is_valid:
                                buffer.append({
                                    "equipment_id": reading.equipment_id,
                                    "sensor_name": reading.sensor_name,
                                    "value": reading.value,
                                    "unit": reading.unit,
                                    "timestamp": reading.timestamp or datetime.now(timezone.utc),
                                })
                            else:
                                record_to_dlq(
                                    equipment_id=data.get("equipment_id"),
                                    sensor_name=data.get("sensor_name"),
                                    raw_payload=data,
                                    error_reason=err or "Validation failure",
                                    source="kafka",
                                )
                        except Exception as parse_err:
                            record_to_dlq(
                                equipment_id=data.get("equipment_id") if isinstance(data, dict) else "UNKNOWN",
                                sensor_name=data.get("sensor_name") if isinstance(data, dict) else "UNKNOWN",
                                raw_payload=data,
                                error_reason=f"Pydantic parsing error: {parse_err}",
                                source="kafka",
                            )

                now = time.time()
                if len(buffer) >= BATCH_SIZE or (buffer and (now - last_flush) >= BATCH_TIMEOUT_SEC):
                    self._flush_batch(buffer)
                    buffer.clear()
                    last_flush = now

            except Exception as exc:
                if self.running:
                    logger.error("Error in Kafka consumer loop: %s", exc)
                    time.sleep(1.0)
