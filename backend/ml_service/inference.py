"""
Real-time Inference Service
============================
Loads trained ML models and runs predictions on live sensor data.
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import joblib
import psycopg2
import psycopg2.extras
import redis
import torch
import torch.nn as nn


# ── LSTM Autoencoder (must match training architecture) ─────
class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, latent_size=16):
        super().__init__()
        self.input_size = input_size
        self.encoder_lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.encoder_fc = nn.Linear(hidden_size, latent_size)
        self.decoder_fc = nn.Linear(latent_size, hidden_size)
        self.decoder_lstm = nn.LSTM(hidden_size, input_size, batch_first=True)
        self.output_fc = nn.Linear(input_size, input_size)

    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        _, (h, _) = self.encoder_lstm(x)
        z = self.encoder_fc(h.squeeze(0))
        h_dec = self.decoder_fc(z)
        decoder_input = h_dec.unsqueeze(1).repeat(1, seq_len, 1)
        decoded, _ = self.decoder_lstm(decoder_input)
        return self.output_fc(decoded)


logger = logging.getLogger("inference")

ARTIFACTS_DIR = Path(os.environ.get("ML_ARTIFACTS_DIR", "/app/ml_artifacts"))
DB_URL = os.environ.get("DATABASE_URL", "postgresql://zydus_user:zydus_pass@localhost:5432/zydus_db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Sensor order per equipment type for consistent feature vectors
SENSOR_ORDER = {
    "manufacturing_line": ["vibration_hz", "temperature_c", "motor_current_a", "pressure_bar", "rotation_speed_rpm"],
    "cold_storage": ["temperature_c", "humidity_percent", "compressor_load_percent", "door_open_count", "power_consumption_kw"],
    "lab_hplc": ["column_pressure_bar", "flow_rate_ml_min", "temperature_c", "run_time_min", "uv_signal_mau"],
    "infusion_pump": ["flow_rate_ml_hr", "pressure_mmhg", "battery_level_percent", "occlusion_flag", "cycle_count"],
    "radiation_unit": ["beam_current_ma", "dose_rate_gy_min", "cooling_temp_c", "arc_voltage_v", "pulse_count"],
}

# Normalization ranges per sensor (from simulator config)
SENSOR_RANGES = {
    "vibration_hz": (10, 60), "temperature_c": (-25, 75), "motor_current_a": (5, 30),
    "pressure_bar": (1, 10), "rotation_speed_rpm": (500, 3000), "humidity_percent": (30, 70),
    "compressor_load_percent": (20, 90), "door_open_count": (0, 5), "power_consumption_kw": (1, 8),
    "column_pressure_bar": (50, 400), "flow_rate_ml_min": (0.1, 5.0), "run_time_min": (0, 120),
    "uv_signal_mau": (0, 2000), "flow_rate_ml_hr": (1, 500), "pressure_mmhg": (10, 300),
    "battery_level_percent": (0, 100), "occlusion_flag": (0, 1), "cycle_count": (0, 10000),
    "beam_current_ma": (1, 50), "dose_rate_gy_min": (0, 10), "cooling_temp_c": (15, 35),
    "arc_voltage_v": (100, 500), "pulse_count": (0, 100000),
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
        try:
            self.redis_client = redis.from_url(REDIS_URL)
            self.redis_client.ping()
            logger.info("Redis connected for prediction caching")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis_client = None

    def _load_models(self):
        """Load all model artifacts."""
        try:
            if (ARTIFACTS_DIR / "isolation_forest.pkl").exists():
                self.isolation_forest = joblib.load(ARTIFACTS_DIR / "isolation_forest.pkl")
                logger.info("  ✓ Isolation Forest loaded")
            if (ARTIFACTS_DIR / "if_scaler.pkl").exists():
                self.if_scaler = joblib.load(ARTIFACTS_DIR / "if_scaler.pkl")

            if (ARTIFACTS_DIR / "lstm_autoencoder.pth").exists():
                with open(ARTIFACTS_DIR / "lstm_threshold.json") as f:
                    self.lstm_config = json.load(f)
                self.lstm_threshold = self.lstm_config["threshold"]
                input_size = self.lstm_config.get("input_size", 5)
                hidden_size = self.lstm_config.get("hidden_size", 64)
                latent_size = self.lstm_config.get("latent_size", 16)
                self.lstm_model = LSTMAutoencoder(input_size, hidden_size, latent_size)
                self.lstm_model.load_state_dict(
                    torch.load(ARTIFACTS_DIR / "lstm_autoencoder.pth",
                               map_location="cpu", weights_only=True))
                self.lstm_model.eval()
                logger.info("  ✓ LSTM Autoencoder loaded")

            if (ARTIFACTS_DIR / "xgb_regressor.pkl").exists():
                self.xgb_regressor = joblib.load(ARTIFACTS_DIR / "xgb_regressor.pkl")
                logger.info("  ✓ XGBoost Regressor loaded")
            if (ARTIFACTS_DIR / "xgb_classifier.pkl").exists():
                self.xgb_classifier = joblib.load(ARTIFACTS_DIR / "xgb_classifier.pkl")
                logger.info("  ✓ XGBoost Classifier loaded")
            if (ARTIFACTS_DIR / "feature_scaler.pkl").exists():
                self.feature_scaler = joblib.load(ARTIFACTS_DIR / "feature_scaler.pkl")

            self.models_loaded = any([self.isolation_forest, self.lstm_model,
                                       self.xgb_regressor, self.xgb_classifier])
            if self.models_loaded:
                logger.info("Models loaded successfully")
            else:
                logger.warning("No model artifacts found — run training first")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.models_loaded = False

    def _get_db(self):
        return psycopg2.connect(DB_URL)

    def _fetch_sensor_data(self, equipment_id, n_timestamps=30):
        """Fetch last N timestamps of sensor data for an equipment."""
        conn = self._get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.type FROM equipment e WHERE e.name = %s
        """, (equipment_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return None, None, None
        eq_db_id, eq_type = row

        cur.execute("""
            SELECT sensor_name, value, timestamp
            FROM sensor_readings
            WHERE equipment_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (eq_db_id, n_timestamps * 5))
        rows = cur.fetchall()
        cur.close(); conn.close()

        if len(rows) < 5:
            return eq_db_id, eq_type, None

        # Pivot: group by timestamp, extract sensor values in order
        sensors = SENSOR_ORDER.get(eq_type, [])
        timestamps = {}
        for sname, value, ts in rows:
            ts_key = ts.isoformat()
            if ts_key not in timestamps:
                timestamps[ts_key] = {}
            timestamps[ts_key][sname] = value

        sorted_ts = sorted(timestamps.keys(), reverse=True)[:n_timestamps]
        matrix = []
        for ts_key in reversed(sorted_ts):
            row_vals = []
            for sensor in sensors:
                val = timestamps[ts_key].get(sensor, 0.0)
                rng = SENSOR_RANGES.get(sensor, (0, 1))
                normalized = (val - rng[0]) / (rng[1] - rng[0] + 1e-10)
                row_vals.append(np.clip(normalized, 0, 1))
            matrix.append(row_vals)

        if len(matrix) < 5:
            return eq_db_id, eq_type, None
        return eq_db_id, eq_type, np.array(matrix, dtype=np.float32)

    def predict(self, equipment_id: str) -> dict:
        """Run full inference pipeline for one equipment."""
        if not self.models_loaded:
            return None

        eq_db_id, eq_type, sensor_matrix = self._fetch_sensor_data(equipment_id)
        if sensor_matrix is None:
            return None

        n_steps, n_sensors = sensor_matrix.shape
        anomaly_score = 0.0
        lstm_score = 0.0
        days_to_failure = 999.0
        failure_prob = 0.0

        # Step 3: Isolation Forest
        if self.isolation_forest is not None:
            try:
                latest = sensor_matrix[-1:].reshape(1, -1)
                if latest.shape[1] != self.isolation_forest.n_features_in_:
                    # Pad or truncate to match
                    expected = self.isolation_forest.n_features_in_
                    padded = np.zeros((1, expected))
                    padded[0, :min(latest.shape[1], expected)] = latest[0, :expected]
                    latest = padded
                raw_score = self.isolation_forest.decision_function(latest)[0]
                anomaly_score = float(np.clip(1 - (raw_score + 0.5), 0, 1))
            except Exception as e:
                logger.debug(f"IF error for {equipment_id}: {e}")

        # Step 4: LSTM Autoencoder
        if self.lstm_model is not None and n_steps >= 10:
            try:
                window = sensor_matrix[-min(n_steps, 30):]
                expected_input = self.lstm_model.input_size
                if n_sensors != expected_input:
                    adapted = np.zeros((len(window), expected_input))
                    adapted[:, :min(n_sensors, expected_input)] = window[:, :expected_input]
                    window = adapted
                if len(window) < 30:
                    pad = np.repeat(window[0:1], 30 - len(window), axis=0)
                    window = np.vstack([pad, window])
                tensor = torch.FloatTensor(window).unsqueeze(0)
                with torch.no_grad():
                    output = self.lstm_model(tensor)
                    error = torch.mean((output - tensor) ** 2).item()
                lstm_score = float(np.clip(error / (self.lstm_threshold + 1e-10), 0, 1))
            except Exception as e:
                logger.debug(f"LSTM error for {equipment_id}: {e}")

        # Step 5-6: XGBoost (engineer rolling features from sensor data)
        if self.xgb_regressor is not None or self.xgb_classifier is not None:
            try:
                features = []
                for col_idx in range(n_sensors):
                    col = sensor_matrix[:, col_idx]
                    features.extend([
                        np.mean(col[-5:]), np.mean(col[-10:]) if len(col) >= 10 else np.mean(col),
                        np.std(col[-5:]), np.std(col[-10:]) if len(col) >= 10 else np.std(col),
                        np.min(col[-10:]) if len(col) >= 10 else np.min(col),
                        np.max(col[-10:]) if len(col) >= 10 else np.max(col),
                    ])
                feat_array = np.array(features).reshape(1, -1)
                expected = self.xgb_regressor.n_features_in_ if self.xgb_regressor else 30
                if feat_array.shape[1] != expected:
                    padded = np.zeros((1, expected))
                    padded[0, :min(feat_array.shape[1], expected)] = feat_array[0, :expected]
                    feat_array = padded
                if self.feature_scaler:
                    feat_array = self.feature_scaler.transform(feat_array)

                if self.xgb_regressor:
                    rul_pred = max(0, self.xgb_regressor.predict(feat_array)[0])
                    days_to_failure = float(rul_pred / 24)  # cycles to days
                if self.xgb_classifier:
                    failure_prob = float(self.xgb_classifier.predict_proba(feat_array)[0][1])
            except Exception as e:
                logger.debug(f"XGBoost error for {equipment_id}: {e}")

        # Step 7: Combine scores
        final_anomaly = (anomaly_score + lstm_score) / 2
        confidence = 1 - abs(anomaly_score - lstm_score)

        result = {
            "equipment_id": equipment_id,
            "anomaly_score": round(final_anomaly, 4),
            "failure_probability": round(failure_prob, 4),
            "days_to_failure": round(days_to_failure, 1),
            "confidence": round(confidence, 4),
            "model_version": "v1",
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Step 8: Save to predictions table
        try:
            conn = self._get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO predictions (equipment_id, anomaly_score, failure_probability,
                                         days_to_failure, confidence)
                VALUES (%s, %s, %s, %s, %s)
            """, (eq_db_id, final_anomaly, failure_prob, days_to_failure, confidence))
            conn.commit()
            cur.close(); conn.close()
        except Exception as e:
            logger.error(f"DB save error: {e}")

        # Step 9: Cache in Redis
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"pred:{equipment_id}", 300,
                    json.dumps(result),
                )
            except Exception as e:
                logger.debug(f"Redis cache error: {e}")

        return result
