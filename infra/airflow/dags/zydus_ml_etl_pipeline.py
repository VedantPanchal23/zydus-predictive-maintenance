from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/zydus"))
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
DAG_SCHEDULE = os.environ.get("AIRFLOW_ML_ETL_SCHEDULE") or None

RAW_INPUTS = [
    "data/raw/nasa_cmapss/train_FD001.txt",
    "data/raw/nasa_cmapss/train_FD002.txt",
    "data/raw/nasa_cmapss/train_FD003.txt",
    "data/raw/nasa_cmapss/train_FD004.txt",
    "data/raw/secom/secom.data",
    "data/raw/secom/secom_labels.data",
]

PROCESSED_OUTPUTS = [
    "cmapss_train.parquet",
    "cmapss_val.parquet",
    "cmapss_test.parquet",
    "secom_train.parquet",
    "secom_val.parquet",
    "secom_test.parquet",
]

MODEL_ARTIFACTS = [
    "feature_scaler.pkl",
    "xgb_regressor.pkl",
    "xgb_classifier.pkl",
    "feature_config.json",
    "isolation_forest.pkl",
    "if_scaler.pkl",
    "lstm_autoencoder.pth",
    "lstm_threshold.json",
]

COMMON_ENV = {
    "PROJECT_ROOT": str(PROJECT_ROOT),
    "PYTHONPATH": str(PROJECT_ROOT),
    "MLFLOW_TRACKING_URI": MLFLOW_URI,
}

default_args = {
    "owner": "platform",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


def _validate_files(base_dir: Path, files: list[str], label: str) -> None:
    missing = []
    empty = []

    for file_name in files:
        file_path = base_dir / file_name
        if not file_path.exists():
            missing.append(str(file_path))
            continue
        if file_path.is_file() and file_path.stat().st_size == 0:
            empty.append(str(file_path))

    if missing or empty:
        parts = []
        if missing:
            parts.append(f"missing: {missing}")
        if empty:
            parts.append(f"empty: {empty}")
        raise AirflowException(f"{label} validation failed ({'; '.join(parts)})")


def validate_raw_inputs() -> None:
    _validate_files(PROJECT_ROOT, RAW_INPUTS, "Raw training inputs")


def validate_mlflow_tracking() -> None:
    health_url = f"{MLFLOW_URI.rstrip('/')}/health"
    try:
        with urlopen(health_url, timeout=10) as response:
            if response.status != 200:
                raise AirflowException(
                    f"MLflow health check returned status {response.status}"
                )
    except (URLError, TimeoutError) as exc:
        raise AirflowException(f"Could not reach MLflow at {health_url}: {exc}") from exc


def validate_processed_outputs() -> None:
    _validate_files(PROCESSED_DIR, PROCESSED_OUTPUTS, "Processed datasets")


def validate_model_artifacts() -> None:
    _validate_files(ARTIFACTS_DIR, MODEL_ARTIFACTS, "Model artifacts")


with DAG(
    dag_id="zydus_ml_etl_pipeline",
    description="Validate inputs, preprocess training data, and train predictive maintenance models.",
    start_date=datetime(2024, 1, 1),
    schedule=DAG_SCHEDULE,
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    default_args=default_args,
    tags=["zydus", "etl", "ml", "production-ready"],
    doc_md="""
    # Zydus ML ETL Pipeline

    This DAG validates raw inputs, confirms the MLflow tracking server is reachable,
    preprocesses the CMAPSS and SECOM datasets, and trains both anomaly-detection
    and failure-prediction models.

    ## Pipeline stages
    1. Validate raw CMAPSS and SECOM files.
    2. Validate the MLflow tracking endpoint.
    3. Preprocess training datasets into parquet outputs.
    4. Validate the processed parquet bundle.
    5. Train anomaly and failure models in parallel.
    6. Verify that all required model artifacts were produced.
    """,
) as dag:
    start = EmptyOperator(task_id="start")

    check_raw_inputs = PythonOperator(
        task_id="validate_raw_inputs",
        python_callable=validate_raw_inputs,
    )

    check_mlflow = PythonOperator(
        task_id="validate_mlflow_tracking",
        python_callable=validate_mlflow_tracking,
    )

    preprocess_data = BashOperator(
        task_id="preprocess_training_data",
        bash_command="python ml/data_prep/prepare_all.py",
        cwd=str(PROJECT_ROOT),
        env=COMMON_ENV,
        append_env=True,
        execution_timeout=timedelta(minutes=30),
    )

    check_processed_outputs = PythonOperator(
        task_id="validate_processed_outputs",
        python_callable=validate_processed_outputs,
    )

    train_anomaly_models = BashOperator(
        task_id="train_anomaly_models",
        bash_command="python ml/models/anomaly_detector.py",
        cwd=str(PROJECT_ROOT),
        env=COMMON_ENV,
        append_env=True,
        execution_timeout=timedelta(hours=1),
    )

    train_failure_models = BashOperator(
        task_id="train_failure_models",
        bash_command="python ml/models/failure_predictor.py",
        cwd=str(PROJECT_ROOT),
        env=COMMON_ENV,
        append_env=True,
        execution_timeout=timedelta(hours=1, minutes=30),
    )

    verify_artifacts = PythonOperator(
        task_id="verify_artifacts",
        python_callable=validate_model_artifacts,
    )

    finish = EmptyOperator(task_id="finish")

    start >> [check_raw_inputs, check_mlflow]
    check_raw_inputs >> preprocess_data >> check_processed_outputs
    check_processed_outputs >> [train_anomaly_models, train_failure_models]
    check_mlflow >> [train_anomaly_models, train_failure_models]
    [train_anomaly_models, train_failure_models] >> verify_artifacts >> finish
