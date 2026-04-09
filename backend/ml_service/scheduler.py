"""
Celery Scheduler - Predictions every 60 seconds
=================================================
"""

import logging
import time

from celery_app import celery_app
from ml_service.inference import InferenceService

logger = logging.getLogger("scheduler")

EQUIPMENT_IDS = [
    "MFG-LINE-01", "MFG-LINE-02", "MFG-LINE-03", "MFG-LINE-04", "MFG-LINE-05",
    "COLD-UNIT-01", "COLD-UNIT-02", "COLD-UNIT-03", "COLD-UNIT-04",
    "LAB-HPLC-01", "LAB-HPLC-02", "LAB-HPLC-03", "LAB-HPLC-04",
    "INF-PUMP-01", "INF-PUMP-02", "INF-PUMP-03", "INF-PUMP-04",
    "RAD-UNIT-01", "RAD-UNIT-02", "RAD-UNIT-03",
]

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
    """Run prediction for all 20 equipment units."""
    service = get_service()
    if not service.models_loaded:
        service._load_models()
    if not service.models_loaded:
        logger.warning("Models not loaded - skipping prediction cycle")
        return {"status": "skipped", "reason": "models_not_loaded"}

    success = 0
    errors = 0
    ts = time.strftime("%H:%M:%S")
    failed_equipment = []

    for eq_id in EQUIPMENT_IDS:
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
        len(EQUIPMENT_IDS),
    )
    return {
        "status": "complete",
        "success": success,
        "errors": errors,
        "failed_equipment": failed_equipment,
    }
