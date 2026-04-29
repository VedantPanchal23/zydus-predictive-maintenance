# Zydus Pharma Oncology Predictive Maintenance System

Real-time predictive maintenance for oncology manufacturing, cold-chain, laboratory, infusion, and radiation equipment. The project streams simulated machine telemetry, stores it in TimescaleDB, runs ML inference, raises alerts and work orders, and exposes the full workflow through a React dashboard plus Airflow, MLflow, and Grafana.

## What The System Does

Think of it as a doctor for machines. It watches equipment vitals such as vibration, temperature, pressure, current, and flow. The ML layer estimates failure probability, anomaly score, and days to failure. When risk becomes operationally important, the platform creates alerts and critical work orders before downtime happens.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, Nginx |
| Backend | FastAPI, WebSocket, JWT/RBAC |
| Streaming | Kafka, Zookeeper |
| Data | TimescaleDB/PostgreSQL, Redis |
| Background jobs | Celery worker and beat |
| ML | scikit-learn, XGBoost, PyTorch |
| Experiment tracking | MLflow |
| Orchestration | Airflow |
| Monitoring | Grafana |
| Local deployment | Docker Compose |

## Quick Start

Run these commands from the repository root.

```powershell
Copy-Item infra\.env.example infra\.env
docker compose -f infra\docker-compose.yml up -d --build
```

The compose stack also runs a one-shot demo bootstrap. It seeds recent telemetry, latest predictions, Redis cache entries, MLflow runs, and a controlled alert/work-order scenario so the project is not empty on first open.

To refresh the demo state before presentation:

```powershell
docker compose -f infra\docker-compose.yml up --build demo-bootstrap airflow-trigger
```

To verify the full system:

```powershell
venv\Scripts\python.exe scripts\docker_smoke_test.py --compose-file infra\docker-compose.yml
```

Expected result: `failures: 0`. Mutation checks are skipped by default so alerts and work orders are not changed during a dry run.

## URLs

| Service | URL | Default login |
| --- | --- | --- |
| Frontend | http://localhost:5173 | `admin / admin123` |
| Backend API docs | http://localhost:8000/docs | use frontend credentials |
| Airflow | http://localhost:8080 | `admin / admin123` |
| MLflow | http://localhost:5000 | none |
| Grafana | http://localhost:3001 | `admin / admin` |
| MinIO console | http://localhost:9001 | `minioadmin / minioadmin` |

## What To Show In A Demo

1. Frontend dashboard at `http://localhost:5173`
2. Equipment detail page with live sensors, prediction, history, alerts, and work orders
3. Alerts and work orders workflow
4. Airflow DAGs:
   - `zydus_ml_etl_pipeline`
   - `zydus_operational_demo_pipeline`
5. MLflow experiment list and run metrics
6. Grafana dashboards in the `Zydus` folder:
   - Equipment Health Overview
   - Sensor Trends Pipeline
   - System Health Overview
7. Postgres proof:

```powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT COUNT(*) FROM sensor_readings;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 5;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 5;"
```

## Test Commands

Backend and integration tests:

```powershell
venv\Scripts\python.exe -m pytest
```

Frontend lint, unit tests, and production build:

```powershell
cd frontend
npm run check
```

Docker smoke test:

```powershell
venv\Scripts\python.exe scripts\docker_smoke_test.py --compose-file infra\docker-compose.yml
```

## Project Layout

```text
backend/                 FastAPI app, ingestion, inference, alert engine, DB bootstrap
frontend/                React dashboard and production Nginx container
infra/                   Docker Compose, Airflow, Grafana provisioning
ml/                      Training code and model artifacts
simulator/               Kafka telemetry simulator
scripts/                 Smoke tests and operational utilities
docs/grafana/            Provisioned Grafana dashboard JSON
SHOWCASE_RUNBOOK.md      Short presentation guide
```

## Equipment Monitored

The demo monitors 20 oncology-relevant assets, including manufacturing lines, cold rooms, ultra-low freezers, HPLC/LCMS equipment, infusion pumps, a linear accelerator, and a CT scanner.

## Production Notes

- Secrets and ports are controlled through `infra/.env`.
- Demo risk scenarios can be toggled with `DEMO_RISK_SCENARIO`.
- Alert thresholds are configurable in `infra/.env`.
- Grafana dashboards and datasource are provisioned automatically.
- MLflow uses a persistent Docker volume, so experiment history survives container restarts.
