"""
Application Configuration Module
================================
Centralized environment variables and system configuration settings.
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
ML_ARTIFACTS_DIR = Path(os.environ.get("ML_ARTIFACTS_DIR", str(BASE_DIR.parent / "ml" / "artifacts")))

# Database & Cache
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db"
    if os.environ.get("DOCKER_CONTAINER") or os.name != "nt"
    else "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
)
DB_POOL_MIN = int(os.environ.get("DB_POOL_MIN", "2"))
DB_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "30"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0" if os.name != "nt" else "redis://localhost:6379/0")

# Kafka
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092" if os.name != "nt" else "localhost:9092")
KAFKA_SENSOR_TOPIC = "equipment.sensors.raw"
KAFKA_CRITICAL_ALERT_TOPIC = "equipment.alerts.critical"
KAFKA_WARNING_ALERT_TOPIC = "equipment.alerts.warning"

# JWT & Security
JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-before-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

# ML & Alert Thresholds
CRITICAL_FAILURE_PROB_THRESHOLD = float(os.environ.get("CRITICAL_FAILURE_PROB_THRESHOLD", "0.80"))
WARNING_FAILURE_PROB_THRESHOLD = float(os.environ.get("WARNING_FAILURE_PROB_THRESHOLD", "0.40"))
CRITICAL_ANOMALY_THRESHOLD = float(os.environ.get("CRITICAL_ANOMALY_THRESHOLD", "0.90"))
WARNING_ANOMALY_THRESHOLD = float(os.environ.get("WARNING_ANOMALY_THRESHOLD", "0.85"))
CRITICAL_DAYS_TO_FAILURE_THRESHOLD = float(os.environ.get("CRITICAL_DAYS_TO_FAILURE_THRESHOLD", "3.0"))
WARNING_DAYS_TO_FAILURE_THRESHOLD = float(os.environ.get("WARNING_DAYS_TO_FAILURE_THRESHOLD", "14.0"))
CRITICAL_ALERT_COOLDOWN_HOURS = int(os.environ.get("CRITICAL_ALERT_COOLDOWN_HOURS", "6"))
WARNING_ALERT_COOLDOWN_HOURS = int(os.environ.get("WARNING_ALERT_COOLDOWN_HOURS", "2"))
PREDICTION_STALE_MINUTES = int(os.environ.get("PREDICTION_STALE_MINUTES", "10"))

PREDICTION_CACHE_TTL_SECONDS = int(os.environ.get('PREDICTION_CACHE_TTL_SECONDS', '300'))
