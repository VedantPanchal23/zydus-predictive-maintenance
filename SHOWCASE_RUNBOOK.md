# Zydus Predictive Maintenance Showcase Runbook

## 1. One-Line Pitch

This system monitors critical oncology equipment in real time, predicts failures before breakdown, creates maintenance alerts and work orders, and proves the pipeline through Airflow, MLflow, Grafana, Kafka, Redis, and TimescaleDB.

## 2. Start The Demo Stack

Run from the repository root:

```powershell
docker compose -f infra\docker-compose.yml up -d --build
```

Refresh the curated demo data before presenting:

```powershell
docker compose -f infra\docker-compose.yml up --build demo-bootstrap airflow-trigger
```

Run the read-only confidence check:

```powershell
venv\Scripts\python.exe scripts\docker_smoke_test.py --compose-file infra\docker-compose.yml
```

Expected summary:

```text
failures: 0
```

## 3. URLs And Credentials

| Service | URL | Login |
| --- | --- | --- |
| Frontend | http://localhost:5173 | `admin / admin123` |
| Backend docs | http://localhost:8000/docs | use frontend token flow |
| Airflow | http://localhost:8080 | `admin / admin123` |
| MLflow | http://localhost:5000 | none |
| Grafana | http://localhost:3001 | `admin / admin` |
| MinIO | http://localhost:9001 | `minioadmin / minioadmin` |

Other app users:

- Engineer: `engineer1 / eng123`
- Viewer: `viewer1 / view123`

## 4. Demo Story

1. Problem
   - Oncology manufacturing and care delivery rely on expensive, safety-critical machines.
   - Sudden failure can delay treatment, spoil temperature-sensitive medicine, or stop production.

2. Solution
   - The platform continuously reads machine vitals.
   - It predicts failure probability, anomaly score, and days to failure.
   - It creates alerts and critical work orders before downtime happens.

3. Live architecture
   - Simulator -> Kafka -> TimescaleDB -> ML inference -> Redis -> Alerts/Work Orders -> Frontend/WebSocket

4. Proof
   - Airflow shows orchestration.
   - MLflow shows experiment tracking.
   - Grafana shows operational dashboards.
   - Postgres proves real rows are flowing.

## 5. What To Show

### Frontend

Open `http://localhost:5173`.

Show:

- Login
- Dashboard
- Equipment cards
- Equipment detail page
- Alerts
- Work orders
- Logs

Say:

- The frontend is data-driven from FastAPI and WebSocket updates.
- The demo state intentionally includes a few risky machines so the workflow is visible.

### Backend APIs

Open `http://localhost:8000/docs`.

Show:

- `/health`
- `/auth/login`
- `/api/equipment`
- `/api/alerts`
- `/api/workorders`
- WebSocket is validated by the smoke test.

Say:

- JWT login and RBAC protect mutating actions.
- The viewer role cannot acknowledge alerts or complete work orders.

### Airflow

Open `http://localhost:8080`.

Show:

- `zydus_ml_etl_pipeline`
- `zydus_operational_demo_pipeline`
- One recent successful DAG run
- Task logs

Say:

- Airflow gives scheduling, dependency control, retries, and visibility into data/ML operations.

### MLflow

Open `http://localhost:5000`.

Show:

- Experiment list
- Runs seeded by the demo bootstrap
- Parameters, metrics, and artifacts

Say:

- MLflow tracks model history so experiments are not lost or hidden in notebooks.

### Grafana

Open `http://localhost:3001`.

Go to the `Zydus` folder and show:

- Equipment Health Overview
- Sensor Trends Pipeline
- System Health Overview

Say:

- Grafana reads TimescaleDB directly through a provisioned datasource.
- These dashboards are automatically loaded by Docker Compose.

### Database Proof

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT COUNT(*) FROM sensor_readings;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT name, current_health, criticality FROM equipment ORDER BY id LIMIT 10;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT equipment_id, failure_probability, anomaly_score, days_to_failure FROM predictions ORDER BY predicted_at DESC LIMIT 5;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT severity, message, created_at FROM alerts ORDER BY created_at DESC LIMIT 5;"
```

## 6. A Simple Data Journey To Explain

Example:

```json
{
  "equipment_id": "COLD-ROOM-01",
  "sensor_name": "temperature_c",
  "value": -18.7,
  "unit": "C",
  "timestamp": "2026-04-29T10:29:07+00:00",
  "is_anomaly": false
}
```

Explain:

1. The simulator generates the reading.
2. Kafka receives it on `equipment.sensors.raw`.
3. The backend consumer stores it in TimescaleDB.
4. The inference service analyzes recent history.
5. The result is stored in `predictions` and cached in Redis.
6. The alert engine creates alerts/work orders only when business thresholds are crossed.
7. The frontend and WebSocket show the latest status.

## 7. 30-Second Viva Answer

This is an end-to-end predictive maintenance platform for oncology equipment. It streams live telemetry, stores time-series data, predicts failure risk using ML, creates alerts and work orders, and displays everything in a real-time dashboard. Airflow handles orchestration, MLflow tracks model experiments, Grafana provides monitoring, and the Docker smoke test verifies the complete system before presentation.

## 8. Recovery Commands

Check containers:

```powershell
docker compose -f infra\docker-compose.yml ps
```

Check logs:

```powershell
docker logs --tail 120 zydus-backend
docker logs --tail 120 zydus-airflow
docker logs --tail 120 zydus-mlflow
docker logs --tail 120 zydus-grafana
```

Reset only the presentation demo state:

```powershell
docker compose -f infra\docker-compose.yml up --build demo-bootstrap airflow-trigger
```
