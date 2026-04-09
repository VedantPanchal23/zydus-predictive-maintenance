# Full System Presentation Runbook

Date: 2026-04-03
Audience: Viva, technical panel, product/demo review
Goal: Present frontend, APIs, Airflow, MLflow, Grafana, and full data pipeline with confidence in one flow.

## 1) Demo Goal in One Sentence

This platform streams live equipment telemetry, predicts failure risk early with ML, generates actionable alerts/work orders, and gives real-time operational visibility through frontend, APIs, and monitoring tools.

## 2) What to Start Before Presentation (15-30 mins earlier)

1. Start full stack:

~~~powershell
cd infra
docker compose up -d --build
~~~

2. Confirm all core services are healthy:

~~~powershell
docker compose ps
~~~

3. Start frontend (if not running in a container):

~~~powershell
cd ../frontend
npm install
npm run dev
~~~

4. Run a quick end-to-end smoke check:

~~~powershell
cd ..
python scripts/docker_smoke_test.py --base-url http://localhost:8000
~~~

5. Keep these browser tabs ready:
- Frontend: http://localhost:5173
- Backend Swagger: http://localhost:8000/docs
- Airflow: http://localhost:8080
- MLflow: http://localhost:5000
- Grafana: http://localhost:3001
- MinIO (optional): http://localhost:9001

## 3) Credentials to Keep Handy

Frontend or Backend:
- Admin: admin / admin123
- Engineer: engineer1 / eng123
- Viewer: viewer1 / view123

Airflow:
- admin / admin123

Grafana:
- admin / admin

Postgres:
- zydus_user / zydus_pass

## 4) 12-Minute Live Demo Script

### Minute 0-1: Problem and Architecture

Say:
- In pharma and hospital operations, unplanned failure causes downtime and safety risk.
- Our system does predictive maintenance: detect early, alert early, act early.

Show:
- Architecture flow from [SHOWCASE_RUNBOOK.md](SHOWCASE_RUNBOOK.md)
- Simulator -> Kafka -> TimescaleDB -> ML -> Redis -> Alerts/Work Orders -> Frontend/WebSocket

### Minute 1-4: Frontend (Main User View)

Show in order:
1. Login page
2. Dashboard with live status
3. Equipment detail page (prediction and history)
4. Alerts page
5. Work orders page
6. Logs page

Say:
- Frontend is fully data-driven from backend APIs and WebSocket updates.
- Users can monitor health, inspect risk, and execute maintenance workflow.

### Minute 4-6: Backend APIs and Security

Open Swagger at http://localhost:8000/docs

Show:
- Health endpoint
- Auth endpoints
- Equipment, predictions, alerts, workorders APIs

Say:
- FastAPI provides all platform APIs.
- JWT auth is enabled.
- RBAC is enforced for mutating operations.

Optional quick proof in terminal:

~~~powershell
python scripts/docker_smoke_test.py --base-url http://localhost:8000
~~~

### Minute 6-8: Airflow Orchestration

Open Airflow and show:
1. DAG list
2. zydus_ml_etl_pipeline
3. Task flow and retries
4. One task log

Say:
- Airflow orchestrates data prep and model training pipeline.
- Gives scheduling, retries, observability, and operational control.

### Minute 8-9: MLflow Tracking

Open MLflow and show:
1. Experiment list
2. Run details
3. Parameters and metrics
4. Artifacts

If runs are missing, generate them before presentation using:

~~~powershell
docker exec zydus-airflow python /opt/zydus/ml/models/anomaly_detector.py
docker exec zydus-airflow python /opt/zydus/ml/models/failure_predictor.py
~~~

Important:
- Do not run docker compose down -v before demo if you want to keep MLflow history.

### Minute 9-10: Grafana Monitoring

Open Grafana and show:
1. Equipment health dashboard
2. Sensor trend panel
3. System health panel

Say:
- Grafana provides operational monitoring for trend and status visibility.

### Minute 10-11: Database Proof

Show real records in Postgres:

~~~powershell
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT COUNT(*) FROM sensor_readings;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 5;"
docker exec zydus-postgres psql -U zydus_user -d zydus_db -c "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 5;"
~~~

Say:
- Data is truly flowing end-to-end, not mocked.

### Minute 11-12: Performance and Close

Use verified numbers:
- Failure classifier accuracy: 95.39%
- AUC-ROC: 98.10%
- Precision: 87.02%
- Recall: 78.02%
- F1: 82.28%

Also say:
- Full Docker smoke passed with 0 failures.
- APIs, infra, RBAC, and live WebSocket behavior were validated.

Close with business impact:
- Reduced downtime
- Early fault detection
- Better maintenance planning
- Better operational visibility

## 5) Fast Recovery Plan If Something Breaks During Demo

1. Backend not reachable:

~~~powershell
cd infra
docker compose ps
docker logs --tail 120 zydus-backend
~~~

2. Frontend not opening:

~~~powershell
cd frontend
npm run dev
~~~

3. Kafka or simulator lag:

~~~powershell
docker logs --tail 120 zydus-kafka
docker logs --tail 120 zydus-simulator
~~~

4. Quick confidence re-check:

~~~powershell
python scripts/docker_smoke_test.py --base-url http://localhost:8000
~~~

## 6) Suggested Final Viva Answer (30 Seconds)

This is an end-to-end predictive maintenance platform for oncology equipment. It ingests live sensor streams, stores time-series data, predicts failure risk with ML, generates alerts and work orders, and shows everything in a real-time dashboard. The failure classifier currently performs strongly with 95.39% accuracy and 98.10% AUC, and our full Docker validation confirms reliable behavior across APIs, Airflow, MLflow, Kafka, database, and monitoring stack.
