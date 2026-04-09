# Zydus Predictive Maintenance Showcase Runbook

## 1. What To Say In One Line

This system monitors critical oncology equipment in real time, predicts failures early using machine learning, raises alerts before breakdowns happen, and shows everything on a live dashboard.

## 2. Demo Story

Use this order in your showcase:

1. Problem statement
   - Hospitals and pharma operations should not wait for important machines to fail.
   - We want early warning, better maintenance planning, and less downtime.

2. System overview
   - Sensor data is generated continuously.
   - Data is streamed through Kafka.
   - It is stored in TimescaleDB.
   - ML models analyze recent sensor history.
   - Alerts and work orders are generated automatically.
   - The frontend dashboard shows current status.
   - Airflow shows ETL and ML pipeline orchestration.
   - MLflow shows experiment and model tracking.

3. Live architecture flow
   - Simulator -> Kafka -> TimescaleDB -> ML inference -> Redis cache -> Alerts/Work Orders -> Frontend/WebSocket

4. Visual components to show
   - Frontend dashboard
   - Equipment detail page
   - Alerts page
   - Work orders page
   - Logs page
   - Airflow DAG UI
   - MLflow experiment UI
   - Database tables
   - Optional: Grafana and MinIO

## 3. URLs To Open

- Frontend app: if running locally, usually `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`
- Airflow: `http://localhost:8080`
- MLflow: `http://localhost:5000`
- Grafana: `http://localhost:3001`
- MinIO console: `http://localhost:9001`

## 4. Demo Credentials

These defaults now come from `infra/.env` for safer local/production-style configuration.

### Frontend / Backend login

Defined in `backend/auth/auth.py`

- Admin: `admin / admin123`
- Engineer: `engineer1 / eng123`
- Viewer: `viewer1 / view123`

### Airflow

- Username: `admin`
- Password: `admin123`

### Grafana

- Username: `admin`
- Password: `admin`

### PostgreSQL / TimescaleDB

- Host: `localhost`
- Port: `5432`
- Database: `zydus_db`
- Username: `zydus_user`
- Password: `zydus_pass`

### MinIO

- Username: `minioadmin`
- Password: `minioadmin`

### MLflow

- No login configured in this local demo setup

## 5. Main Components To Explain

### Frontend

- React-based dashboard for live monitoring
- Shows equipment health, predictions, alerts, work orders, and logs

### Backend

- FastAPI APIs
- WebSocket for live updates
- JWT-based login

### Kafka

- Receives raw sensor readings in real time
- Decouples sensor producer and backend consumer

### TimescaleDB

- Stores time-series sensor readings
- Stores relational data like predictions, alerts, work orders, equipment

### Redis

- Stores latest predictions for fast access

### Celery

- Runs prediction and alert generation in background

### Airflow

- Orchestrates ETL and ML pipeline
- Current DAG:
  - preprocess training data
  - train anomaly models
  - train failure models
  - verify model artifacts

### MLflow

- Tracks experiments, training runs, and logged models

## 6. Data Sources

1. Simulated live equipment data from `simulator/sensor_simulator.py`
2. Open-Meteo ambient temperature for cold storage adjustment
3. NASA CMAPSS dataset for failure prediction training
4. SECOM dataset for anomaly detection training
5. Internal generated data:
   - predictions
   - alerts
   - work orders

## 7. One Data Point You Can Explain

Example raw sensor reading:

```json
{
  "equipment_id": "COLD-UNIT-01",
  "equipment_type": "cold_storage",
  "sensor_name": "temperature_c",
  "value": -18.7,
  "unit": "°C",
  "timestamp": "2026-04-02T10:29:07+00:00",
  "is_anomaly": false
}
```

Explain it like this:

1. The simulator generates this sensor value.
2. It is sent to Kafka topic `equipment.sensors.raw`.
3. The Kafka consumer reads it and stores it in `sensor_readings`.
4. The ML service looks at a recent set of readings, not just one row.
5. It calculates:
   - anomaly score
   - failure probability
   - days to failure
6. That result is stored in `predictions` and cached in Redis.
7. If risk is high, `alerts` and `work_orders` are created.
8. The dashboard and WebSocket show the latest status.

## 8. Tables To Show

Main business tables:

- `equipment`
- `sensor_readings`
- `predictions`
- `alerts`
- `work_orders`

### Command to list tables

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\dt"
```

### Command to describe each table

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\d equipment"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\d sensor_readings"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\d predictions"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\d alerts"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\d work_orders"
```

### Command to show sample rows

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM equipment LIMIT 10;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 10;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 10;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT 10;"
```

## 9. What To Show In Airflow

Open `http://localhost:8080`

Show:

1. DAG list
2. `zydus_ml_etl_pipeline`
3. Task flow:
   - `preprocess_training_data`
   - `train_anomaly_models`
   - `train_failure_models`
   - `verify_artifacts`
4. Run history
5. Logs of one task

Explain:

- Airflow is used to automate ETL plus ML training steps.
- It gives scheduling, monitoring, retries, and visibility.

## 10. What To Show In MLflow

Open `http://localhost:5000`

Show:

1. Experiment list
2. Anomaly detection runs
3. Failure prediction runs
4. Parameters and metrics
5. Logged models

Explain:

- MLflow stores training history, model metrics, and artifacts.
- It helps compare runs and track which model version is being used.

## 11. What To Show In Frontend

1. Login page
2. Dashboard
3. Equipment cards
4. Live sensor rows
5. Equipment detail page
6. Alerts page
7. Work orders page
8. Logs page

Explain:

- This is the main user-facing monitoring screen.
- It is data-driven, not hardcoded business data.
- Live sensor updates come through WebSocket.

## 12. Very Short Viva Answer

This project is a predictive maintenance platform for oncology equipment. It collects live sensor data, stores it, analyzes it with machine learning, predicts failure risk, generates alerts and work orders, and shows the results on a dashboard. We also use Airflow for ETL and ML pipeline orchestration, and MLflow for experiment tracking.

## 13. Backup Commands Before Demo

Check all containers:

```powershell
cd infra
docker compose ps
```

Check database tables:

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "\dt"
```

Check Airflow user:

```powershell
docker exec zydus-airflow airflow users list
```

Check latest alerts:

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 5;"
```

Check latest predictions:

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 5;"
```

## 14. Final Tip For Demo

Do not start with tools first.

Start with:

1. Problem
2. Solution
3. Architecture
4. One data point journey
5. Frontend
6. Airflow
7. MLflow
8. Database tables
9. Final business impact

End with:

- reduced downtime
- early detection
- better maintenance planning
- improved operational visibility
