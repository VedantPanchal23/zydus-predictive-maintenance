"""
Real-time Inference Service
============================
Loads trained ML models and runs predictions on live sensor data.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg2
import redis
import torch
import torch.nn as nn

from common.reliability import retry_call


class LSTMAutoencoder(nn.Module):
    """Architecture must match the training script exactly."""

    def __init__(self, input_size=5, hidden_size=64, latent_size=16):
        super().__init__()
        self.input_size = input_size
        self.encoder_lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.encoder_fc = nn.Linear(hidden_size, latent_size)
        self.decoder_fc = nn.Linear(latent_size, hidden_size)
        self.decoder_lstm = nn.LSTM(hidden_size, input_size, batch_first=True)
        self.output_fc = nn.Linear(input_size, input_size)

    def forward(self, x):
        _, (hidden, _) = self.encoder_lstm(x)
        latent = self.encoder_fc(hidden.squeeze(0))
        decoded_hidden = self.decoder_fc(latent)
        decoder_input = decoded_hidden.unsqueeze(1).repeat(1, x.shape[1], 1)
        decoded, _ = self.decoder_lstm(decoder_input)
        return self.output_fc(decoded)


logger = logging.getLogger("inference")

ARTIFACTS_DIR = Path(os.environ.get("ML_ARTIFACTS_DIR", "/app/ml_artifacts"))
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
PREDICTION_CACHE_TTL_SECONDS = int(os.environ.get("PREDICTION_CACHE_TTL_SECONDS", "300"))
DB_RETRIES = int(os.environ.get("ML_DB_RETRIES", "3"))
REDIS_RETRIES = int(os.environ.get("ML_REDIS_RETRIES", "3"))

SENSOR_ORDER = {
    "manufacturing_line": [
        "vibration_hz",
        "temperature_c",
        "motor_current_a",
        "pressure_bar",
        "rotation_speed_rpm",
    ],
    "cold_storage": [
        "temperature_c",
        "humidity_percent",
        "compressor_load_percent",
        "door_open_count",
        "power_consumption_kw",
    ],
    "lab_hplc": [
        "column_pressure_bar",
        "flow_rate_ml_min",
        "temperature_c",
        "run_time_min",
        "uv_signal_mau",
    ],
    "infusion_pump": [
        "flow_rate_ml_hr",
        "pressure_mmhg",
        "battery_level_percent",
        "occlusion_flag",
        "cycle_count",
    ],
    "radiation_unit": [
        "beam_current_ma",
        "dose_rate_gy_min",
        "cooling_temp_c",
        "arc_voltage_v",
        "pulse_count",
    ],
}

SENSOR_RANGES = {
    "vibration_hz": (10, 60),
    "temperature_c": (-25, 75),
    "motor_current_a": (5, 30),
    "pressure_bar": (1, 10),
    "rotation_speed_rpm": (500, 3000),
    "humidity_percent": (30, 70),
    "compressor_load_percent": (20, 90),
    "door_open_count": (0, 5),
    "power_consumption_kw": (1, 8),
    "column_pressure_bar": (50, 400),
    "flow_rate_ml_min": (0.1, 5.0),
    "run_time_min": (0, 120),
    "uv_signal_mau": (0, 2000),
    "flow_rate_ml_hr": (1, 500),
    "pressure_mmhg": (10, 300),
    "battery_level_percent": (0, 100),
    "occlusion_flag": (0, 1),
    "cycle_count": (0, 10000),
    "beam_current_ma": (1, 50),
    "dose_rate_gy_min": (0, 10),
    "cooling_temp_c": (15, 35),
    "arc_voltage_v": (100, 500),
    "pulse_count": (0, 100000),
}


class InferenceService:
    """Loads ML models and runs real-time predictions."""

    def __init__(self):
        self.isolation_forest = None
        self.lstm_model = None
        self.lstm_threshold = None
        self.lstm_config = None
        self.xgb_regressor = None
        self.xgb_classifier = None
        self.feature_scaler = None
        self.if_scaler = None
        self.redis_client = None
        self.models_loaded = False

        self._load_models()
        self._connect_redis()

    def _connect_redis(self):
        def connect():
            client = redis.from_url(REDIS_URL)
            client.ping()
            return client

        try:
            self.redis_client = retry_call(
                connect,
                retries=REDIS_RETRIES,
                initial_delay=1.0,
                retry_exceptions=(redis.RedisError,),
                logger=logger,
                operation_name="redis connection",
            )
            logger.info("Redis connected for prediction caching")
        except redis.RedisError as exc:
            logger.warning("Redis not available for prediction caching: %s", exc)
            self.redis_client = None

    def _load_models(self):
        """Load all model artifacts from disk."""
        try:
            if (ARTIFACTS_DIR / "isolation_forest.pkl").exists():
                self.isolation_forest = joblib.load(ARTIFACTS_DIR / "isolation_forest.pkl")
                logger.info("  - Isolation Forest loaded")

            if (ARTIFACTS_DIR / "if_scaler.pkl").exists():
                self.if_scaler = joblib.load(ARTIFACTS_DIR / "if_scaler.pkl")

            if (ARTIFACTS_DIR / "lstm_autoencoder.pth").exists():
                with open(ARTIFACTS_DIR / "lstm_threshold.json", encoding="utf-8") as handle:
                    self.lstm_config = json.load(handle)

                self.lstm_threshold = self.lstm_config["threshold"]
                input_size = self.lstm_config.get("input_size", 5)
                hidden_size = self.lstm_config.get("hidden_size", 64)
                latent_size = self.lstm_config.get("latent_size", 16)

                self.lstm_model = LSTMAutoencoder(input_size, hidden_size, latent_size)
                self.lstm_model.load_state_dict(
                    torch.load(
                        ARTIFACTS_DIR / "lstm_autoencoder.pth",
                        map_location="cpu",
                        weights_only=True,
                    )
                )
                self.lstm_model.eval()
                logger.info("  - LSTM Autoencoder loaded")

            if (ARTIFACTS_DIR / "xgb_regressor.pkl").exists():
                self.xgb_regressor = joblib.load(ARTIFACTS_DIR / "xgb_regressor.pkl")
                logger.info("  - XGBoost Regressor loaded")

            if (ARTIFACTS_DIR / "xgb_classifier.pkl").exists():
                self.xgb_classifier = joblib.load(ARTIFACTS_DIR / "xgb_classifier.pkl")
                logger.info("  - XGBoost Classifier loaded")

            if (ARTIFACTS_DIR / "feature_scaler.pkl").exists():
                self.feature_scaler = joblib.load(ARTIFACTS_DIR / "feature_scaler.pkl")

            self.models_loaded = any(
                [
                    self.isolation_forest is not None,
                    self.lstm_model is not None,
                    self.xgb_regressor is not None,
                    self.xgb_classifier is not None,
                ]
            )
            if self.models_loaded:
                logger.info("Models loaded successfully")
            else:
                logger.warning("No model artifacts found - run training first")
        except Exception as exc:
            logger.error("Error loading model artifacts: %s", exc)
            self.models_loaded = False

    def _get_db(self):
        return retry_call(
            lambda: psycopg2.connect(DB_URL),
            retries=DB_RETRIES,
            initial_delay=1.0,
            retry_exceptions=(psycopg2.OperationalError, psycopg2.InterfaceError),
            logger=logger,
            operation_name="database connection",
        )

    def _fetch_sensor_data(self, equipment_id: str, n_timestamps: int = 30):
        """Fetch the latest sensor matrix for one equipment."""
        conn = self._get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, type FROM equipment WHERE name = %s", (equipment_id,))
                row = cur.fetchone()
                if not row:
                    logger.warning("Equipment %s not found in database", equipment_id)
                    return None, None, None

                eq_db_id, eq_type = row
                sensors = SENSOR_ORDER.get(eq_type, [])
                if not sensors:
                    logger.warning("No sensor mapping configured for equipment type %s", eq_type)
                    return eq_db_id, eq_type, None

                cur.execute(
                    """
                    SELECT sensor_name, value, timestamp
                    FROM sensor_readings
                    WHERE equipment_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (eq_db_id, n_timestamps * max(len(sensors), 5)),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        if len(rows) < len(sensors):
            logger.debug("Skipping %s - insufficient sensor history", equipment_id)
            return eq_db_id, eq_type, None

        grouped_by_timestamp = {}
        for sensor_name, value, timestamp in rows:
            timestamp_key = timestamp.isoformat()
            grouped_by_timestamp.setdefault(timestamp_key, {})[sensor_name] = value

        sorted_timestamps = sorted(grouped_by_timestamp.keys(), reverse=True)[:n_timestamps]
        matrix = []
        for timestamp_key in reversed(sorted_timestamps):
            normalized_row = []
            for sensor_name in sensors:
                raw_value = grouped_by_timestamp[timestamp_key].get(sensor_name, 0.0)
                sensor_min, sensor_max = SENSOR_RANGES.get(sensor_name, (0.0, 1.0))
                normalized = (raw_value - sensor_min) / (sensor_max - sensor_min + 1e-10)
                normalized_row.append(float(np.clip(normalized, 0.0, 1.0)))
            matrix.append(normalized_row)

        if len(matrix) < 5:
            logger.debug("Skipping %s - not enough aligned sensor windows", equipment_id)
            return eq_db_id, eq_type, None

        return eq_db_id, eq_type, np.array(matrix, dtype=np.float32)

    def _save_prediction(self, eq_db_id: int, result: dict) -> None:
        def persist():
            conn = self._get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO predictions (
                            equipment_id, anomaly_score, failure_probability,
                            days_to_failure, confidence
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            eq_db_id,
                            result["anomaly_score"],
                            result["failure_probability"],
                            result["days_to_failure"],
                            result["confidence"],
                        ),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        retry_call(
            persist,
            retries=DB_RETRIES,
            initial_delay=1.0,
            retry_exceptions=(psycopg2.Error,),
            logger=logger,
            operation_name=f"prediction persistence for equipment {eq_db_id}",
        )

    def _cache_prediction(self, equipment_id: str, result: dict) -> None:
        if self.redis_client is None:
            self._connect_redis()

        if self.redis_client is None:
            return

        try:
            self.redis_client.setex(
                f"pred:{equipment_id}",
                PREDICTION_CACHE_TTL_SECONDS,
                json.dumps(result),
            )
        except redis.RedisError as exc:
            logger.warning("Redis cache write failed for %s: %s", equipment_id, exc)
            self.redis_client = None

    def predict(self, equipment_id: str) -> dict | None:
        """Run the full inference pipeline for one equipment."""
        if not self.models_loaded:
            return None

        eq_db_id, eq_type, sensor_matrix = self._fetch_sensor_data(equipment_id)
        if sensor_matrix is None:
            return None

        n_steps, n_sensors = sensor_matrix.shape
        anomaly_signals = []
        days_to_failure = 999.0
        failure_prob = 0.0

        if self.isolation_forest is not None:
            try:
                latest = sensor_matrix[-1:].reshape(1, -1)
                expected = self.isolation_forest.n_features_in_
                if latest.shape[1] != expected:
                    padded = np.zeros((1, expected))
                    padded[0, : min(latest.shape[1], expected)] = latest[0, :expected]
                    latest = padded

                raw_score = self.isolation_forest.decision_function(latest)[0]
                if_score = float(np.clip(1 - (raw_score + 0.5), 0.0, 1.0))
                anomaly_signals.append(if_score)
            except Exception as exc:
                logger.debug("Isolation Forest failed for %s: %s", equipment_id, exc)

        if self.lstm_model is not None and n_steps >= 10:
            try:
                window = sensor_matrix[-min(n_steps, 30):]
                expected_input = self.lstm_model.input_size
                if n_sensors != expected_input:
                    adapted = np.zeros((len(window), expected_input))
                    adapted[:, : min(n_sensors, expected_input)] = window[:, :expected_input]
                    window = adapted

                if len(window) < 30:
                    padding = np.repeat(window[0:1], 30 - len(window), axis=0)
                    window = np.vstack([padding, window])

                tensor = torch.FloatTensor(window).unsqueeze(0)
                with torch.no_grad():
                    output = self.lstm_model(tensor)
                    error = torch.mean((output - tensor) ** 2).item()
                lstm_score = float(np.clip(error / (self.lstm_threshold + 1e-10), 0.0, 1.0))
                anomaly_signals.append(lstm_score)
            except Exception as exc:
                logger.debug("LSTM autoencoder failed for %s: %s", equipment_id, exc)

        if self.xgb_regressor is not None or self.xgb_classifier is not None:
            try:
                features = []
                for col_idx in range(n_sensors):
                    col = sensor_matrix[:, col_idx]
                    features.extend(
                        [
                            np.mean(col[-5:]),
                            np.mean(col[-10:]) if len(col) >= 10 else np.mean(col),
                            np.std(col[-5:]),
                            np.std(col[-10:]) if len(col) >= 10 else np.std(col),
                            np.min(col[-10:]) if len(col) >= 10 else np.min(col),
                            np.max(col[-10:]) if len(col) >= 10 else np.max(col),
                        ]
                    )

                feat_array = np.array(features).reshape(1, -1)
                expected = self.xgb_regressor.n_features_in_ if self.xgb_regressor else 30
                if feat_array.shape[1] != expected:
                    padded = np.zeros((1, expected))
                    padded[0, : min(feat_array.shape[1], expected)] = feat_array[0, :expected]
                    feat_array = padded

                if self.feature_scaler is not None:
                    if hasattr(self.feature_scaler, "feature_names_in_"):
                        feature_names = list(self.feature_scaler.feature_names_in_)
                        scaler_expected = len(feature_names)
                        if feat_array.shape[1] != scaler_expected:
                            adjusted = np.zeros((1, scaler_expected))
                            adjusted[0, : min(feat_array.shape[1], scaler_expected)] = feat_array[0, :scaler_expected]
                            feat_array = adjusted
                        feat_frame = pd.DataFrame(feat_array, columns=feature_names)
                        feat_array = self.feature_scaler.transform(feat_frame)
                    else:
                        feat_array = self.feature_scaler.transform(feat_array)

                if self.xgb_regressor is not None:
                    rul_pred = max(0.0, float(self.xgb_regressor.predict(feat_array)[0]))
                    days_to_failure = rul_pred / 24.0

                if self.xgb_classifier is not None:
                    failure_prob = float(self.xgb_classifier.predict_proba(feat_array)[0][1])
            except Exception as exc:
                logger.debug("XGBoost scoring failed for %s: %s", equipment_id, exc)

        final_anomaly = float(np.mean(anomaly_signals)) if anomaly_signals else 0.0
        if len(anomaly_signals) >= 2:
            confidence = float(np.clip(1 - abs(anomaly_signals[0] - anomaly_signals[1]), 0.0, 1.0))
        else:
            confidence = 1.0 if anomaly_signals else 0.0

        result = {
            "equipment_id": equipment_id,
            "equipment_type": eq_type,
            "anomaly_score": round(final_anomaly, 4),
            "failure_probability": round(float(np.clip(failure_prob, 0.0, 1.0)), 4),
            "days_to_failure": round(max(0.0, days_to_failure), 1),
            "confidence": round(confidence, 4),
            "model_version": "v1",
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self._save_prediction(eq_db_id, result)
        except psycopg2.Error as exc:
            logger.error("Prediction persistence failed for %s: %s", equipment_id, exc)

        self._cache_prediction(equipment_id, result)
        return result
