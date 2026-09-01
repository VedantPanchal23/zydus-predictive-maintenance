"""Re-export canonical Ingestion Kafka Consumer."""
from ingestion.kafka_consumer import SensorDataConsumer, main

__all__ = ["SensorDataConsumer", "main"]
