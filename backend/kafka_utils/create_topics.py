"""
Kafka Topic Management
======================
Creates all required Kafka topics on application startup.
"""

import os
import time
import logging

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

logger = logging.getLogger("kafka-topics")

TOPICS = [
    {
        "name": "equipment.sensors.raw",
        "partitions": 3,
        "replication": 1,
        "description": "All raw sensor readings from 20 equipment units",
    },
    {
        "name": "equipment.alerts.critical",
        "partitions": 1,
        "replication": 1,
        "description": "Failure predictions above 80%",
    },
    {
        "name": "equipment.alerts.warning",
        "partitions": 1,
        "replication": 1,
        "description": "Failure predictions 40-80%",
    },
    {
        "name": "maintenance.workorders",
        "partitions": 1,
        "replication": 1,
        "description": "Auto-generated maintenance work orders",
    },
]


def create_topics(max_retries: int = 10, retry_delay: float = 5.0):
    """Create all Kafka topics. Retries if Kafka is not yet available."""
    broker = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    logger.info(f"Creating Kafka topics on {broker}...")

    admin = None
    for attempt in range(1, max_retries + 1):
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=broker,
                client_id="zydus-topic-creator",
            )
            logger.info("Connected to Kafka admin")
            break
        except NoBrokersAvailable:
            logger.warning(
                f"Kafka not available (attempt {attempt}/{max_retries}). "
                f"Retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Kafka admin error: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    if admin is None:
        logger.error("Failed to connect to Kafka after all retries")
        return False

    # Get existing topics
    existing = admin.list_topics()

    for topic_config in TOPICS:
        name = topic_config["name"]
        if name in existing:
            logger.info(f"  ✓ Topic '{name}' already exists")
            continue

        try:
            new_topic = NewTopic(
                name=name,
                num_partitions=topic_config["partitions"],
                replication_factor=topic_config["replication"],
            )
            admin.create_topics([new_topic])
            logger.info(f"  ✓ Created topic '{name}' — {topic_config['description']}")
        except TopicAlreadyExistsError:
            logger.info(f"  ✓ Topic '{name}' already exists")
        except Exception as e:
            logger.error(f"  ✗ Failed to create topic '{name}': {e}")

    admin.close()
    logger.info("All Kafka topics ready")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    create_topics()