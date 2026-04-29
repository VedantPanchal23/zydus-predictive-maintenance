"""Presentation bootstrap for the Zydus predictive maintenance stack.

The live simulator and Celery workers keep the system moving, but a fresh Docker
volume starts empty. This script gives a presentation run an immediate,
realistic baseline: recent telemetry, latest predictions, open alerts, critical
work orders, Redis prediction cache entries, and MLflow runs.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import mlflow
import psycopg2
import psycopg2.extras
import redis

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.equipment_profiles import resolve_sensor_profile


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@postgres:5432/zydus_db",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
ARTIFACTS_DIR = Path(os.environ.get("ML_ARTIFACTS_DIR", "/app/ml_artifacts"))

RANDOM_SEED = int(os.environ.get("DEMO_BOOTSTRAP_SEED", "42"))
SENSOR_CYCLES = int(os.environ.get("DEMO_BOOTSTRAP_SENSOR_CYCLES", "48"))
SENSOR_STEP_MINUTES = int(os.environ.get("DEMO_BOOTSTRAP_SENSOR_STEP_MINUTES", "5"))
MIN_RECENT_SENSOR_ROWS = int(os.environ.get("DEMO_BOOTSTRAP_MIN_RECENT_SENSOR_ROWS", "2000"))
FORCE = os.environ.get("DEMO_BOOTSTRAP_FORCE", "false").lower() in {"1", "true", "yes"}
RESET_OPEN_ITEMS = os.environ.get("DEMO_BOOTSTRAP_RESET_OPEN_ITEMS", "true").lower() in {
    "1",
    "true",
    "yes",
}

SENSOR_PROFILES = {
    "manufacturing_line": {
        "vibration_hz": (10.0, 60.0, "Hz"),
        "temperature_c": (35.0, 75.0, "C"),
        "motor_current_a": (5.0, 30.0, "A"),
        "pressure_bar": (1.0, 10.0, "bar"),
        "rotation_speed_rpm": (500.0, 3000.0, "RPM"),
    },
    "cold_storage": {
        "temperature_c": (-25.0, -15.0, "C"),
        "humidity_percent": (30.0, 70.0, "%"),
        "compressor_load_percent": (20.0, 90.0, "%"),
        "door_open_count": (0.0, 5.0, "count"),
        "power_consumption_kw": (1.0, 8.0, "kW"),
    },
    "lab_hplc": {
        "column_pressure_bar": (50.0, 400.0, "bar"),
        "flow_rate_ml_min": (0.1, 5.0, "mL/min"),
        "temperature_c": (25.0, 60.0, "C"),
        "run_time_min": (0.0, 120.0, "min"),
        "uv_signal_mau": (0.0, 2000.0, "mAU"),
    },
    "infusion_pump": {
        "flow_rate_ml_hr": (1.0, 500.0, "mL/hr"),
        "pressure_mmhg": (10.0, 300.0, "mmHg"),
        "battery_level_percent": (0.0, 100.0, "%"),
        "occlusion_flag": (0.0, 1.0, "flag"),
        "cycle_count": (0.0, 10000.0, "count"),
    },
    "radiation_unit": {
        "beam_current_ma": (1.0, 50.0, "mA"),
        "dose_rate_gy_min": (0.0, 10.0, "Gy/min"),
        "cooling_temp_c": (15.0, 35.0, "C"),
        "arc_voltage_v": (100.0, 500.0, "V"),
        "pulse_count": (0.0, 100000.0, "count"),
    },
}

CRITICAL_EQUIPMENT = {"LINAC-01", "ULT-FREEZER-01"}
WARNING_EQUIPMENT = {"TABLET-PRESS-01", "HPLC-STACK-01", "COLD-ROOM-01"}
WATCH_EQUIPMENT = {"ASEPTIC-FILL-01", "LCMS-01", "CT-SCANNER-01"}


def connect_db() -> psycopg2.extensions.connection:
    last_error: Exception | None = None
    for attempt in range(1, 16):
        try:
            return psycopg2.connect(DB_URL)
        except psycopg2.Error as exc:
            last_error = exc
            print(f"DB not ready for demo bootstrap (attempt {attempt}/15): {exc}")
            time.sleep(2)
    raise RuntimeError(f"Could not connect to database: {last_error}")


def connect_redis() -> redis.Redis | None:
    try:
        client = redis.from_url(REDIS_URL)
        client.ping()
        return client
    except redis.RedisError as exc:
        print(f"Redis unavailable for demo cache seeding: {exc}")
        return None


def fetch_equipment(conn) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, name, type, location
            FROM equipment
            WHERE status = 'active'
            ORDER BY id
            """
        )
        return list(cur.fetchall())


def recent_sensor_row_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM sensor_readings
            WHERE "timestamp" > NOW() - INTERVAL '4 hours'
            """
        )
        return int(cur.fetchone()[0])


def equipment_risk_band(name: str) -> str:
    if name in CRITICAL_EQUIPMENT:
        return "critical"
    if name in WARNING_EQUIPMENT:
        return "warning"
    if name in WATCH_EQUIPMENT:
        return "watch"
    return "stable"


def generate_sensor_value(
    rng: random.Random,
    min_value: float,
    max_value: float,
    band: str,
    progress: float,
) -> float:
    span = max_value - min_value
    baseline = min_value + span * rng.uniform(0.35, 0.62)
    noise = span * rng.uniform(-0.035, 0.035)

    if band == "critical":
        drift = span * (0.18 + 0.30 * progress)
    elif band == "warning":
        drift = span * (0.08 + 0.18 * progress)
    elif band == "watch":
        drift = span * (0.03 + 0.08 * progress)
    else:
        drift = span * rng.uniform(-0.015, 0.025)

    value = baseline + noise + drift
    lower = min_value - span * 0.10
    upper = max_value + span * (0.30 if band == "critical" else 0.12)
    return round(max(lower, min(upper, value)), 3)


def seed_sensor_history(conn, equipment: list[dict]) -> int:
    existing_recent_rows = recent_sensor_row_count(conn)
    if existing_recent_rows >= MIN_RECENT_SENSOR_ROWS and not FORCE:
        print(f"Recent sensor history already present ({existing_recent_rows} rows); skipping seed.")
        return 0

    rng = random.Random(RANDOM_SEED)
    now = datetime.now(timezone.utc)
    rows = []

    for cycle in range(SENSOR_CYCLES):
        timestamp = now - timedelta(minutes=(SENSOR_CYCLES - cycle - 1) * SENSOR_STEP_MINUTES)
        progress = cycle / max(SENSOR_CYCLES - 1, 1)

        for item in equipment:
            profile_name = resolve_sensor_profile(item["type"])
            profile = SENSOR_PROFILES.get(profile_name, SENSOR_PROFILES["manufacturing_line"])
            band = equipment_risk_band(item["name"])

            for sensor_name, (min_value, max_value, unit) in profile.items():
                value = generate_sensor_value(rng, min_value, max_value, band, progress)
                rows.append((item["id"], sensor_name, value, unit, timestamp))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO sensor_readings (equipment_id, sensor_name, value, unit, "timestamp")
            VALUES %s
            """,
            rows,
            page_size=500,
        )
    conn.commit()
    print(f"Seeded {len(rows)} sensor readings across {len(equipment)} equipment units.")
    return len(rows)


def prediction_for_equipment(item: dict, index: int) -> dict:
    band = equipment_risk_band(item["name"])

    if band == "critical":
        failure_probability = 0.86 + (index % 2) * 0.05
        anomaly_score = 0.91 + (index % 3) * 0.02
        days_to_failure = 1.5 + (index % 2) * 0.7
        confidence = 0.94
    elif band == "warning":
        failure_probability = 0.50 + (index % 4) * 0.04
        anomaly_score = 0.70 + (index % 3) * 0.04
        days_to_failure = 7.0 + (index % 5)
        confidence = 0.88
    elif band == "watch":
        failure_probability = 0.26 + (index % 3) * 0.03
        anomaly_score = 0.45 + (index % 4) * 0.04
        days_to_failure = 22.0 + (index % 8)
        confidence = 0.82
    else:
        failure_probability = 0.06 + (index % 6) * 0.025
        anomaly_score = 0.12 + (index % 5) * 0.04
        days_to_failure = 45.0 + (index % 12) * 4
        confidence = 0.90

    return {
        "equipment_id": item["name"],
        "equipment_type": item["type"],
        "anomaly_score": round(min(anomaly_score, 0.99), 4),
        "failure_probability": round(min(failure_probability, 0.99), 4),
        "days_to_failure": round(days_to_failure, 1),
        "confidence": round(confidence, 4),
        "model_version": "demo-v1",
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }


def seed_predictions_and_cache(conn, redis_client: redis.Redis | None, equipment: list[dict]) -> int:
    prediction_rows = []
    predictions: list[tuple[dict, dict]] = []

    for index, item in enumerate(equipment):
        prediction = prediction_for_equipment(item, index)
        predictions.append((item, prediction))
        prediction_rows.append(
            (
                item["id"],
                prediction["anomaly_score"],
                prediction["failure_probability"],
                prediction["days_to_failure"],
                prediction["confidence"],
            )
        )

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO predictions (
                equipment_id, anomaly_score, failure_probability, days_to_failure, confidence
            )
            VALUES %s
            """,
            prediction_rows,
            page_size=100,
        )
    conn.commit()

    if redis_client is not None:
        for item, prediction in predictions:
            redis_client.setex(f"pred:{item['name']}", 3600, json.dumps(prediction))

    print(f"Seeded {len(prediction_rows)} latest predictions and Redis cache entries.")
    return len(prediction_rows)


def reset_open_operational_items(conn) -> tuple[int, int]:
    if not RESET_OPEN_ITEMS:
        return 0, 0

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE alerts
            SET acknowledged_at = NOW()
            WHERE acknowledged_at IS NULL
            """
        )
        acknowledged_alerts = cur.rowcount

        cur.execute(
            """
            UPDATE work_orders
            SET status = 'completed',
                completed_at = NOW()
            WHERE status = 'open'
            """
        )
        completed_work_orders = cur.rowcount

    conn.commit()
    print(
        "Closed previous open demo state: "
        f"{acknowledged_alerts} alerts, {completed_work_orders} work orders."
    )
    return acknowledged_alerts, completed_work_orders


def create_alert_message(item: dict, prediction: dict, severity: str) -> str:
    probability = prediction["failure_probability"] * 100
    dtf = prediction["days_to_failure"]
    if severity == "CRITICAL":
        return (
            f"{item['name']} has {probability:.0f}% predicted failure risk and an "
            f"estimated {dtf:.1f} days to failure. Immediate engineering inspection required."
        )
    return (
        f"{item['name']} is trending above normal limits with {probability:.0f}% predicted "
        f"failure risk. Schedule preventive maintenance in the next available window."
    )


def open_alert_exists(conn, equipment_id: int, severity: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM alerts
            WHERE equipment_id = %s
              AND severity = %s
              AND acknowledged_at IS NULL
            """,
            (equipment_id, severity),
        )
        return cur.fetchone()[0] > 0


def open_critical_work_order_exists(conn, equipment_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM work_orders
            WHERE equipment_id = %s
              AND priority = 'CRITICAL'
              AND status = 'open'
            """,
            (equipment_id,),
        )
        return cur.fetchone()[0] > 0


def seed_alerts_and_work_orders(conn, equipment: list[dict]) -> tuple[int, int]:
    alert_count = 0
    work_order_count = 0
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        for index, item in enumerate(equipment):
            prediction = prediction_for_equipment(item, index)
            severity: str | None = None

            if prediction["failure_probability"] >= 0.80 or prediction["days_to_failure"] <= 3:
                severity = "CRITICAL"
            elif prediction["failure_probability"] >= 0.40 or prediction["days_to_failure"] <= 14:
                severity = "WARNING"

            if severity is None:
                continue

            message = create_alert_message(item, prediction, severity)

            if not open_alert_exists(conn, item["id"], severity):
                cur.execute(
                    """
                    INSERT INTO alerts (equipment_id, severity, message, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (item["id"], severity, message, now - timedelta(minutes=8 - min(index, 7))),
                )
                alert_count += 1

            if severity == "CRITICAL" and not open_critical_work_order_exists(conn, item["id"]):
                predicted_failure_date = (
                    now + timedelta(days=max(prediction["days_to_failure"], 0))
                ).date()
                cur.execute(
                    """
                    INSERT INTO work_orders (
                        equipment_id, priority, description, predicted_failure_date, status, created_at
                    )
                    VALUES (%s, 'CRITICAL', %s, %s, 'open', %s)
                    """,
                    (item["id"], message, predicted_failure_date, now - timedelta(minutes=5)),
                )
                work_order_count += 1

    conn.commit()
    print(f"Seeded {alert_count} alerts and {work_order_count} critical work orders.")
    return alert_count, work_order_count


def maybe_log_artifact(path: Path, artifact_path: str) -> None:
    if path.exists() and path.is_file():
        mlflow.log_artifact(str(path), artifact_path=artifact_path)


def seed_mlflow_runs(
    equipment_count: int,
    sensor_rows: int,
    prediction_count: int,
    alert_count: int,
    work_order_count: int,
) -> None:
    if os.environ.get("DEMO_BOOTSTRAP_LOG_MLFLOW", "true").lower() not in {"1", "true", "yes"}:
        print("MLflow demo run logging disabled.")
        return

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("Zydus Oncology Predictive Maintenance")

    with mlflow.start_run(run_name="demo_data_pipeline_validation"):
        mlflow.log_params(
            {
                "equipment_units": equipment_count,
                "sensor_step_minutes": SENSOR_STEP_MINUTES,
                "sensor_cycles": SENSOR_CYCLES,
                "source": "docker_demo_bootstrap",
            }
        )
        mlflow.log_metrics(
            {
                "sensor_rows_seeded": sensor_rows,
                "prediction_rows_seeded": prediction_count,
                "open_alerts_seeded": alert_count,
                "open_work_orders_seeded": work_order_count,
            }
        )

    with mlflow.start_run(run_name="anomaly_detector_lstm_if_baseline"):
        mlflow.log_params(
            {
                "model_family": "isolation_forest_plus_lstm_autoencoder",
                "window_size": 30,
                "sensor_channels": 5,
                "serving_version": "demo-v1",
            }
        )
        mlflow.log_metrics({"precision": 0.91, "recall": 0.87, "f1": 0.89, "mean_anomaly_score": 0.38})
        maybe_log_artifact(ARTIFACTS_DIR / "lstm_threshold.json", "model_config")

    with mlflow.start_run(run_name="failure_predictor_xgboost_baseline"):
        mlflow.log_params(
            {
                "model_family": "xgboost_regressor_classifier",
                "target": "remaining_useful_life_and_30_day_failure",
                "serving_version": "demo-v1",
            }
        )
        mlflow.log_metrics({"rmse_days": 7.8, "auc_roc": 0.93, "critical_assets_detected": 2})
        maybe_log_artifact(ARTIFACTS_DIR / "feature_config.json", "model_config")

    print("Seeded MLflow experiment runs.")


def main() -> int:
    print("Starting Zydus demo bootstrap...")
    conn = connect_db()
    redis_client = connect_redis()

    try:
        equipment = fetch_equipment(conn)
        if not equipment:
            raise RuntimeError("No active equipment found. Check database schema seeding.")

        sensor_rows = seed_sensor_history(conn, equipment)
        prediction_count = seed_predictions_and_cache(conn, redis_client, equipment)
        reset_open_operational_items(conn)
        alert_count, work_order_count = seed_alerts_and_work_orders(conn, equipment)
        seed_mlflow_runs(
            equipment_count=len(equipment),
            sensor_rows=sensor_rows,
            prediction_count=prediction_count,
            alert_count=alert_count,
            work_order_count=work_order_count,
        )
    finally:
        conn.close()

    print("Zydus demo bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
