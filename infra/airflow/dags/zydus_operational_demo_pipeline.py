from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import psycopg2
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/zydus"))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
ML_ARTIFACTS_DIR = os.environ.get("ML_ARTIFACTS_DIR", str(PROJECT_ROOT / "ml" / "artifacts"))

COMMON_ENV = {
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "PYTHONPATH": f"{PROJECT_ROOT}:{PROJECT_ROOT / 'backend'}",
    "DATABASE_URL": DATABASE_URL,
    "REDIS_URL": REDIS_URL,
    "MLFLOW_TRACKING_URI": MLFLOW_URI,
    "ML_ARTIFACTS_DIR": ML_ARTIFACTS_DIR,
}

default_args = {
    "owner": "platform",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def validate_runtime_services() -> None:
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM equipment WHERE UPPER(status) = 'ACTIVE'")
                equipment_count = cur.fetchone()[0]
    except psycopg2.Error as exc:
        raise AirflowException(f"Postgres runtime database is unavailable: {exc}") from exc

    if equipment_count < 20:
        raise AirflowException(f"Expected 20 active equipment units, found {equipment_count}")

    health_url = f"{MLFLOW_URI.rstrip('/')}/health"
    try:
        with urlopen(health_url, timeout=10) as response:
            if response.status != 200:
                raise AirflowException(f"MLflow health returned {response.status}")
    except (URLError, TimeoutError) as exc:
        raise AirflowException(f"MLflow is unavailable at {health_url}: {exc}") from exc


def validate_demo_state() -> None:
    checks = {
        "sensor_readings": "SELECT COUNT(*) FROM sensor_readings WHERE timestamp > NOW() - INTERVAL '4 hours'",
        "predictions": "SELECT COUNT(*) FROM predictions WHERE predicted_at > NOW() - INTERVAL '4 hours'",
        "open_alerts": "SELECT COUNT(*) FROM alerts WHERE acknowledged_at IS NULL",
        "open_work_orders": "SELECT COUNT(*) FROM work_orders WHERE status = 'open'",
    }

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            counts = {}
            for label, query in checks.items():
                cur.execute(query)
                counts[label] = cur.fetchone()[0]

    missing = [label for label, count in counts.items() if count <= 0]
    if missing:
        raise AirflowException(f"Demo state validation failed: {counts}")

    print(f"Demo state is ready: {counts}")


with DAG(
    dag_id="zydus_operational_demo_pipeline",
    description="Bootstraps and validates presentation-ready operational telemetry, alerts, and MLflow runs.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=20),
    default_args=default_args,
    tags=["zydus", "demo", "operations", "presentation"],
    doc_md="""
    # Zydus Operational Demo Pipeline

    This fast DAG prepares a fresh Docker environment for demonstration:

    1. Validates Postgres and MLflow availability.
    2. Seeds recent equipment telemetry, predictions, alerts, and work orders.
    3. Logs MLflow showcase runs.
    4. Verifies that Grafana and the frontend have live data to query.
    """,
) as dag:
    start = EmptyOperator(task_id="start")

    validate_services = PythonOperator(
        task_id="validate_runtime_services",
        python_callable=validate_runtime_services,
    )

    bootstrap_demo_state = BashOperator(
        task_id="bootstrap_demo_state",
        bash_command="python backend/db/demo_bootstrap.py",
        cwd=str(PROJECT_ROOT),
        env=COMMON_ENV,
        append_env=True,
        execution_timeout=timedelta(minutes=10),
    )

    validate_state = PythonOperator(
        task_id="validate_demo_state",
        python_callable=validate_demo_state,
    )

    finish = EmptyOperator(task_id="finish")

    start >> validate_services >> bootstrap_demo_state >> validate_state >> finish
