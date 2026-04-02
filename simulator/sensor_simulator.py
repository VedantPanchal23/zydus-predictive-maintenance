"""
Zydus Pharma Oncology — Sensor Simulator
=========================================
Simulates 20 oncology equipment streaming sensor data every 5 seconds into Kafka.
Injects anomalies (gradual drift, sudden spike, oscillation) into ~20% of readings.
Fetches real ambient temperature from Open-Meteo API for cold storage units.
"""

import json
import time
import random
import os
import logging
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import httpx

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sensor-simulator")

# ── Equipment Configuration ─────────────────────────────────
EQUIPMENT = {
    "MFG-LINE-01": {"type": "manufacturing_line", "sensors": {
        "vibration_hz": (10, 60),
        "temperature_c": (35, 75),
        "motor_current_a": (5, 30),
        "pressure_bar": (1, 10),
        "rotation_speed_rpm": (500, 3000),
    }},
    "MFG-LINE-02": {"type": "manufacturing_line", "sensors": {
        "vibration_hz": (10, 60), "temperature_c": (35, 75),
        "motor_current_a": (5, 30), "pressure_bar": (1, 10),
        "rotation_speed_rpm": (500, 3000),
    }},
    "MFG-LINE-03": {"type": "manufacturing_line", "sensors": {
        "vibration_hz": (10, 60), "temperature_c": (35, 75),
        "motor_current_a": (5, 30), "pressure_bar": (1, 10),
        "rotation_speed_rpm": (500, 3000),
    }},
    "MFG-LINE-04": {"type": "manufacturing_line", "sensors": {
        "vibration_hz": (10, 60), "temperature_c": (35, 75),
        "motor_current_a": (5, 30), "pressure_bar": (1, 10),
        "rotation_speed_rpm": (500, 3000),
    }},
    "MFG-LINE-05": {"type": "manufacturing_line", "sensors": {
        "vibration_hz": (10, 60), "temperature_c": (35, 75),
        "motor_current_a": (5, 30), "pressure_bar": (1, 10),
        "rotation_speed_rpm": (500, 3000),
    }},
    "COLD-UNIT-01": {"type": "cold_storage", "sensors": {
        "temperature_c": (-25, -15),
        "humidity_percent": (30, 70),
        "compressor_load_percent": (20, 90),
        "door_open_count": (0, 5),
        "power_consumption_kw": (1, 8),
    }},
    "COLD-UNIT-02": {"type": "cold_storage", "sensors": {
        "temperature_c": (-25, -15), "humidity_percent": (30, 70),
        "compressor_load_percent": (20, 90),
        "door_open_count": (0, 5), "power_consumption_kw": (1, 8),
    }},
    "COLD-UNIT-03": {"type": "cold_storage", "sensors": {
        "temperature_c": (-25, -15), "humidity_percent": (30, 70),
        "compressor_load_percent": (20, 90),
        "door_open_count": (0, 5), "power_consumption_kw": (1, 8),
    }},
    "COLD-UNIT-04": {"type": "cold_storage", "sensors": {
        "temperature_c": (-25, -15), "humidity_percent": (30, 70),
        "compressor_load_percent": (20, 90),
        "door_open_count": (0, 5), "power_consumption_kw": (1, 8),
    }},
    "LAB-HPLC-01": {"type": "lab_hplc", "sensors": {
        "column_pressure_bar": (50, 400),
        "flow_rate_ml_min": (0.1, 5.0),
        "temperature_c": (25, 60),
        "run_time_min": (0, 120),
        "uv_signal_mau": (0, 2000),
    }},
    "LAB-HPLC-02": {"type": "lab_hplc", "sensors": {
        "column_pressure_bar": (50, 400), "flow_rate_ml_min": (0.1, 5.0),
        "temperature_c": (25, 60), "run_time_min": (0, 120),
        "uv_signal_mau": (0, 2000),
    }},
    "LAB-HPLC-03": {"type": "lab_hplc", "sensors": {
        "column_pressure_bar": (50, 400), "flow_rate_ml_min": (0.1, 5.0),
        "temperature_c": (25, 60), "run_time_min": (0, 120),
        "uv_signal_mau": (0, 2000),
    }},
    "LAB-HPLC-04": {"type": "lab_hplc", "sensors": {
        "column_pressure_bar": (50, 400), "flow_rate_ml_min": (0.1, 5.0),
        "temperature_c": (25, 60), "run_time_min": (0, 120),
        "uv_signal_mau": (0, 2000),
    }},
    "INF-PUMP-01": {"type": "infusion_pump", "sensors": {
        "flow_rate_ml_hr": (1, 500),
        "pressure_mmhg": (10, 300),
        "battery_level_percent": (0, 100),
        "occlusion_flag": (0, 1),
        "cycle_count": (0, 10000),
    }},
    "INF-PUMP-02": {"type": "infusion_pump", "sensors": {
        "flow_rate_ml_hr": (1, 500), "pressure_mmhg": (10, 300),
        "battery_level_percent": (0, 100),
        "occlusion_flag": (0, 1), "cycle_count": (0, 10000),
    }},
    "INF-PUMP-03": {"type": "infusion_pump", "sensors": {
        "flow_rate_ml_hr": (1, 500), "pressure_mmhg": (10, 300),
        "battery_level_percent": (0, 100),
        "occlusion_flag": (0, 1), "cycle_count": (0, 10000),
    }},
    "INF-PUMP-04": {"type": "infusion_pump", "sensors": {
        "flow_rate_ml_hr": (1, 500), "pressure_mmhg": (10, 300),
        "battery_level_percent": (0, 100),
        "occlusion_flag": (0, 1), "cycle_count": (0, 10000),
    }},
    "RAD-UNIT-01": {"type": "radiation_unit", "sensors": {
        "beam_current_ma": (1, 50),
        "dose_rate_gy_min": (0, 10),
        "cooling_temp_c": (15, 35),
        "arc_voltage_v": (100, 500),
        "pulse_count": (0, 100000),
    }},
    "RAD-UNIT-02": {"type": "radiation_unit", "sensors": {
        "beam_current_ma": (1, 50), "dose_rate_gy_min": (0, 10),
        "cooling_temp_c": (15, 35), "arc_voltage_v": (100, 500),
        "pulse_count": (0, 100000),
    }},
    "RAD-UNIT-03": {"type": "radiation_unit", "sensors": {
        "beam_current_ma": (1, 50), "dose_rate_gy_min": (0, 10),
        "cooling_temp_c": (15, 35), "arc_voltage_v": (100, 500),
        "pulse_count": (0, 100000),
    }},
}

# ── Sensor unit mapping ─────────────────────────────────────
SENSOR_UNITS = {
    "vibration_hz": "Hz",
    "temperature_c": "°C",
    "motor_current_a": "A",
    "pressure_bar": "bar",
    "rotation_speed_rpm": "RPM",
    "humidity_percent": "%",
    "compressor_load_percent": "%",
    "door_open_count": "count",
    "power_consumption_kw": "kW",
    "column_pressure_bar": "bar",
    "flow_rate_ml_min": "mL/min",
    "run_time_min": "min",
    "uv_signal_mau": "mAU",
    "flow_rate_ml_hr": "mL/hr",
    "pressure_mmhg": "mmHg",
    "battery_level_percent": "%",
    "occlusion_flag": "flag",
    "cycle_count": "count",
    "beam_current_ma": "mA",
    "dose_rate_gy_min": "Gy/min",
    "cooling_temp_c": "°C",
    "arc_voltage_v": "V",
    "pulse_count": "count",
}


class SensorSimulator:
    """Simulates sensor data for 20 oncology equipment units."""

    def __init__(self):
        self.kafka_broker = os.environ.get("KAFKA_BROKER", "localhost:9092")
        self.producer = None
        self.topic = "equipment.sensors.raw"

        # Per equipment+sensor anomaly state tracking
        self.anomaly_states = {}

        # Open-Meteo ambient temperature
        self.ambient_temp = None
        self.last_weather_fetch = 0

        self._connect_kafka()

    # ── Kafka Connection ────────────────────────────────────
    def _connect_kafka(self):
        """Connect to Kafka with retry logic."""
        while True:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_broker,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",
                    retries=3,
                )
                logger.info(f"Connected to Kafka at {self.kafka_broker}")
                return
            except NoBrokersAvailable:
                logger.warning(f"Kafka not available at {self.kafka_broker}. Retrying in 5s...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Kafka connection error: {e}. Retrying in 5s...")
                time.sleep(5)

    # ── Open-Meteo Weather ──────────────────────────────────
    def _fetch_ambient_temperature(self):
        """Fetch real ambient temperature from Open-Meteo API (every 10 minutes)."""
        now = time.time()
        if now - self.last_weather_fetch < 600:
            return

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=22.99&longitude=72.60&current=temperature_2m"
            )
            resp = httpx.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.ambient_temp = data["current"]["temperature_2m"]
            self.last_weather_fetch = now
            logger.info(f"🌡  Open-Meteo ambient temperature: {self.ambient_temp}°C (Ahmedabad)")
        except Exception as e:
            logger.warning(f"Failed to fetch ambient temperature: {e}")

    # ── Value Generation ────────────────────────────────────
    def _generate_value(self, equipment_name, sensor_name, min_val, max_val):
        """Generate a sensor value — 80% normal, 20% anomaly injection."""
        key = f"{equipment_name}_{sensor_name}"
        state = self.anomaly_states.get(key)

        is_anomaly = False

        # ─ Continue an active anomaly ─
        if state and state["remaining"] > 0:
            is_anomaly = True
            atype = state["type"]

            if atype == "gradual_drift":
                drift_factor = 1 + (0.05 * state["step"])
                value = state["base"] * drift_factor
                state["step"] += 1
            elif atype == "sudden_spike":
                value = max_val * 3
            elif atype == "oscillation":
                value = min_val if state["step"] % 2 == 0 else max_val
                state["step"] += 1

            state["remaining"] -= 1
            if state["remaining"] <= 0:
                self.anomaly_states[key] = None
            else:
                self.anomaly_states[key] = state

        # ─ Maybe start a NEW anomaly (20% chance) ─
        elif random.random() < 0.2:
            is_anomaly = True
            atype = random.choice(["gradual_drift", "sudden_spike", "oscillation"])
            normal_value = random.uniform(min_val, max_val)

            if atype == "gradual_drift":
                value = normal_value * 1.05
                self.anomaly_states[key] = {
                    "type": "gradual_drift",
                    "remaining": 19,
                    "base": normal_value,
                    "step": 2,
                }
            elif atype == "sudden_spike":
                value = max_val * 3
                self.anomaly_states[key] = None  # spike is 1 reading only
            elif atype == "oscillation":
                value = min_val
                self.anomaly_states[key] = {
                    "type": "oscillation",
                    "remaining": 9,
                    "base": None,
                    "step": 1,
                }

        # ─ Normal reading (80%) ─
        else:
            value = random.uniform(min_val, max_val)

        # ─ Apply ambient temperature offset for cold storage ─
        if (
            equipment_name in ("COLD-UNIT-01", "COLD-UNIT-02")
            and sensor_name == "temperature_c"
            and self.ambient_temp is not None
        ):
            # Higher ambient temp → harder cooling → warmer inside
            offset = (self.ambient_temp - 25) * 0.1
            value += offset

        return round(value, 2), is_anomaly

    # ── Main Loop ───────────────────────────────────────────
    def run(self):
        """Main simulation loop — publishes readings every 5 seconds."""
        total_sensors = sum(len(e["sensors"]) for e in EQUIPMENT.values())
        logger.info(f"Starting sensor simulator")
        logger.info(f"  Equipment: {len(EQUIPMENT)} units")
        logger.info(f"  Sensors:   {total_sensors} total")
        logger.info(f"  Interval:  5 seconds")
        logger.info(f"  Topic:     {self.topic}")

        cycle = 0
        while True:
            cycle += 1
            self._fetch_ambient_temperature()

            count = 0
            anomaly_count = 0
            ts = datetime.now(timezone.utc).isoformat()

            for eq_name, eq_info in EQUIPMENT.items():
                for sensor_name, (min_val, max_val) in eq_info["sensors"].items():
                    value, is_anomaly = self._generate_value(
                        eq_name, sensor_name, min_val, max_val
                    )

                    reading = {
                        "equipment_id": eq_name,
                        "equipment_type": eq_info["type"],
                        "sensor_name": sensor_name,
                        "value": value,
                        "unit": SENSOR_UNITS.get(sensor_name, ""),
                        "timestamp": ts,
                        "is_anomaly": is_anomaly,
                    }

                    try:
                        self.producer.send(self.topic, value=reading)
                    except Exception as e:
                        logger.error(f"Failed to send reading: {e}")
                        self._connect_kafka()
                        self.producer.send(self.topic, value=reading)

                    count += 1
                    if is_anomaly:
                        anomaly_count += 1

            self.producer.flush()
            logger.info(
                f"[Cycle {cycle}] Published {count} readings "
                f"({anomaly_count} anomalies) for {len(EQUIPMENT)} equipment"
            )
            time.sleep(5)


# ── Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    simulator = SensorSimulator()
    simulator.run()
