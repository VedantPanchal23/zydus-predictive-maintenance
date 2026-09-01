"""
Automated ML Prediction & Alert Scheduling Engine
==================================================
Runs condition monitoring predictions and alert evaluations periodically.
Can run as an internal async worker or distributed Celery task.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time

from common.equipment_registry import list_active_equipment_ids
from ml.inference import InferenceService
from ml.alert_engine import run_alert_engine

logger = logging.getLogger("scheduler")

_inference_service: InferenceService | None = None
_scheduler_task: asyncio.Task | None = None
_running = False


def get_inference_service() -> InferenceService:
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service


def run_prediction_cycle() -> dict:
    """Execute real-time ML inference for all active equipment."""
    svc = get_inference_service()
    if not svc.models_loaded:
        svc._load_models()

    equipment_ids = list_active_equipment_ids()
    success_count = 0
    skipped_count = 0
    ts = time.strftime("%H:%M:%S")

    for eq_id in equipment_ids:
        try:
            res = svc.predict(eq_id)
            if res:
                success_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            logger.error("Prediction error on %s: %s", eq_id, exc)
            skipped_count += 1

    logger.info(
        "[%s] Scheduled prediction cycle: %s predictions, %s skipped",
        ts,
        success_count,
        skipped_count,
    )
    return {"predicted": success_count, "skipped": skipped_count}


async def background_scheduler_loop():
    """Asynchronous background scheduler loop inside FastAPI lifespan."""
    logger.info("Started unified background ML scheduler loop")
    last_pred = 0.0
    last_alert = 0.0

    while _running:
        try:
            now = time.time()

            # Prediction cycle every 60 seconds
            if now - last_pred >= 60.0:
                await asyncio.to_thread(run_prediction_cycle)
                last_pred = now

            # Alert evaluation cycle every 30 seconds
            if now - last_alert >= 30.0:
                await asyncio.to_thread(run_alert_engine)
                last_alert = now

            await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc)
            await asyncio.sleep(5.0)


def start_scheduler():
    global _scheduler_task, _running
    if not _running:
        _running = True
        _scheduler_task = asyncio.create_task(background_scheduler_loop(), name="ml-scheduler")


def stop_scheduler():
    global _scheduler_task, _running
    _running = False
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()


# Alias for Celery compatibility
run_all_predictions = run_prediction_cycle
run_inference_cycle = run_prediction_cycle
