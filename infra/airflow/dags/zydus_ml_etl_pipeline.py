from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "/opt/zydus")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")


with DAG(
    dag_id="zydus_ml_etl_pipeline",
    description="Preprocess raw datasets and train predictive maintenance models.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["zydus", "etl", "ml"],
    doc_md="""
    # Zydus ML ETL Pipeline

    This DAG prepares the raw CMAPSS and SECOM datasets and then trains the
    anomaly-detection and failure-prediction models used by the application.

    ## Expected raw files
    - `data/raw/nasa_cmapss/train_FD001.txt` through `train_FD004.txt`
    - `data/raw/secom/secom.data`
    - `data/raw/secom/secom_labels.data`

    ## Outputs
    - Processed parquet files under `data/processed`
    - Trained model artifacts under `ml/artifacts`
    """,
) as dag:
    start = EmptyOperator(task_id="start")

    preprocess_data = BashOperator(
        task_id="preprocess_training_data",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python ml/data_prep/prepare_all.py"
        ),
    )

    train_anomaly_models = BashOperator(
        task_id="train_anomaly_models",
        bash_command=(
            f"export MLFLOW_TRACKING_URI={MLFLOW_URI} && "
            f"cd {PROJECT_ROOT} && "
            "python ml/models/anomaly_detector.py"
        ),
    )

    train_failure_models = BashOperator(
        task_id="train_failure_models",
        bash_command=(
            f"export MLFLOW_TRACKING_URI={MLFLOW_URI} && "
            f"cd {PROJECT_ROOT} && "
            "python ml/models/failure_predictor.py"
        ),
    )

    verify_artifacts = BashOperator(
        task_id="verify_artifacts",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python - <<'PY'\n"
            "from pathlib import Path\n"
            "root = Path.cwd() / 'ml' / 'artifacts'\n"
            "required = [\n"
            "    'feature_scaler.pkl',\n"
            "    'xgb_regressor.pkl',\n"
            "    'xgb_classifier.pkl',\n"
            "    'feature_config.json',\n"
            "    'isolation_forest.pkl',\n"
            "    'if_scaler.pkl',\n"
            "    'lstm_autoencoder.pth',\n"
            "    'lstm_threshold.json',\n"
            "]\n"
            "missing = [name for name in required if not (root / name).exists()]\n"
            "if missing:\n"
            "    raise SystemExit(f'Missing artifacts: {missing}')\n"
            "print('All expected ML artifacts are present.')\n"
            "PY"
        ),
    )

    finish = EmptyOperator(task_id="finish")

    start >> preprocess_data
    preprocess_data >> train_anomaly_models >> train_failure_models >> verify_artifacts >> finish
