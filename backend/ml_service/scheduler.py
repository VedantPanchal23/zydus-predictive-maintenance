"""
Celery Scheduler - Predictions every 60 seconds
=================================================
"""

import logging
import time

from celery_app import celery_app
from common.equipment_registry import list_active_equipment_ids
from ml_service.inference import InferenceService

logger = logging.getLogger("scheduler")

_service = None


def get_service():
    global _service
    if _service is None:
        _service = InferenceService()
    return _service


@celery_app.task(
    name="ml_service.scheduler.run_all_predictions",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def run_all_predictions(self):
    """Run prediction for all active equipment units."""
    service = get_service()
    if not service.models_loaded:
        service._load_models()
    if not service.models_loaded:
        logger.warning("Models not loaded - skipping prediction cycle")
        return {"status": "skipped", "reason": "models_not_loaded"}

    equipment_ids = list_active_equipment_ids()
    if not equipment_ids:
        logger.warning("No active equipment found - skipping prediction cycle")
        return {"status": "skipped", "reason": "no_equipment"}

    success = 0
    errors = 0
    ts = time.strftime("%H:%M:%S")
    failed_equipment = []

    for eq_id in equipment_ids:
        try:
            result = service.predict(eq_id)
            if result:
                success += 1
            else:
                errors += 1
                failed_equipment.append(eq_id)
        except Exception as e:
            logger.error("Prediction error for %s: %s", eq_id, e)
            errors += 1
            failed_equipment.append(eq_id)

    logger.info(
        "[%s] Predictions complete: %s/%s equipment processed",
        ts,
        success,
        len(equipment_ids),
    )
    return {
        "status": "complete",
        "success": success,
        "errors": errors,
        "failed_equipment": failed_equipment,
    }
