"""
Celery Application Configuration
==================================
"""

import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "zydus",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["ml_service.scheduler", "ml_service.alert_engine"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    task_default_retry_delay=30,
    result_expires=3600,
    beat_schedule={
        "run-predictions-every-60s": {
            "task": "ml_service.scheduler.run_all_predictions",
            "schedule": 60.0,
        },
        "run-alerts-every-30s": {
            "task": "ml_service.alert_engine.run_alert_engine",
            "schedule": 30.0,
        },
    },
)
