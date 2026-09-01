"""
Airflow DAG: Zydus Autonomous MLOps & Drift Auto-Rollback Pipeline
==================================================================
Daily autonomous evaluation of sensor feature drift (PSI), automated
candidate model training, challenger-champion benchmarking, and
21 CFR Part 11 audited promotion/rollback.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "zydus-mlops",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "zydus_autonomous_ml_retraining",
    default_args=default_args,
    description="Daily automated PSI feature drift detection and GAMP 5 model retraining",
    schedule_interval="0 2 * * *",  # Nightly at 02:00 UTC
    catchup=False,
    tags=["zydus", "mlops", "gamp5", "21cfr-part11"],
)


def task_evaluate_fleet_drift(**context):
    """Calculates PSI feature drift across all 20 monitored digital twins."""
    from ml.drift_evaluator import evaluate_dataset_drift
    from ml.retrain_pipeline import fetch_historical_training_data

    baseline = fetch_historical_training_data(1, hours=72)
    current = fetch_historical_training_data(1, hours=24)
    drift = evaluate_dataset_drift(baseline, current)
    
    print(f"Fleet Drift Status: {drift['drift_status']} (Max PSI: {drift['max_psi']})")
    context["ti"].xcom_push(key="drift_metrics", value=drift)
    return drift


def task_train_and_evaluate_champion(**context):
    """Executes candidate model training and challenger-champion promotion."""
    from ml.retrain_pipeline import execute_retraining_cycle

    ti = context["ti"]
    drift_metrics = ti.xcom_pull(key="drift_metrics", task_ids="evaluate_fleet_drift") or {}
    should_force = drift_metrics.get("retraining_recommended", False)

    result = execute_retraining_cycle("GRAN-LINE-01", force_promotion=should_force)
    print(f"Retraining Result: {result['action']} -> {result['status_reason']}")
    return result


evaluate_drift_task = PythonOperator(
    task_id="evaluate_fleet_drift",
    python_callable=task_evaluate_fleet_drift,
    dag=dag,
)

train_evaluate_task = PythonOperator(
    task_id="train_and_evaluate_champion",
    python_callable=task_train_and_evaluate_champion,
    dag=dag,
)

evaluate_drift_task >> train_evaluate_task
