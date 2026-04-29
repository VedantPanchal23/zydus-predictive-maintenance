#  Zydus Pharma Oncology — AI Predictive Maintenance System

> Real-time AI-powered predictive maintenance for 20 critical oncology equipment units at Zydus Pharma Oncology Pvt. Ltd.

## 🎯 Overview

This system monitors drug manufacturing lines, cold storage units, HPLC machines, infusion pumps, and radiation units — streaming live sensor data through Apache Kafka, storing it in TimescaleDB, and running AI/ML models to detect anomalies and predict equipment failures before they happen.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI |
| Frontend | React (JavaScript) |
| Streaming | Apache Kafka |
| Database | TimescaleDB (PostgreSQL 15) |
| Cache | Redis |
| ML/AI | scikit-learn, XGBoost, PyTorch |
| Experiment Tracking | MLflow |
| Object Storage | MinIO |
| Monitoring | Grafana |
| Deployment | Docker Compose |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for ML data preparation)

### 1. Configure environment
```bash
cp infra/.env.example infra/.env
```

Update `infra/.env` before production-style runs, especially:
- `JWT_SECRET`
- `AIRFLOW_WEBSERVER_SECRET_KEY`
- `AIRFLOW_FERNET_KEY`
- admin passwords for Airflow, Grafana, and MinIO

### 2. Start all services
```bash
cd infra
docker compose up -d
```

If you moved the project to a new folder and see duplicate containers/volumes, run a full reset first:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/docker_full_reset.ps1
```

### 3. Verify services
```bash
docker compose ps
```

Core runtime services should show as **healthy**. `airflow-init` is expected to exit successfully after bootstrapping the metadata database and admin user.

### 4. Access services

| Service | URL |
|---------|-----|
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Airflow | http://localhost:8080 |
| Grafana | http://localhost:3001 |
| MLflow | http://localhost:5000 |
| MinIO Console | http://localhost:9001 |

### 5. Prepare ML datasets
```bash
pip install pandas numpy scikit-learn pyarrow
python ml/data_prep/prepare_all.py
```

### 6. Validate the frontend
```bash
cd frontend
npm install
npm run check
```

### 7. Run full Docker smoke audit (read-only)
```bash
python scripts/docker_smoke_test.py --compose-file infra/docker-compose.yml
```

This mode validates APIs and infrastructure without mutating alerts/workorders.

### 8. Optional mutation checks
```bash
python scripts/docker_smoke_test.py --compose-file infra/docker-compose.yml --allow-mutations
```

## Production Hardening Notes

- Docker Compose now reads secrets and admin credentials from `infra/.env`.
- MLflow uses a persistent backend store and artifact directory under the `mlflow_data` volume.
- Airflow runs as separate `init`, `webserver`, and `scheduler` services with a dedicated metadata database.
- The ML ETL DAG validates raw inputs, checks MLflow health, validates processed parquet outputs, and verifies the full artifact bundle after training.

## 📁 Project Structure

```text
zydus-predictive-maintenance/
├── .github/              # CI/CD Workflows
│   └── workflows/        # GitHub Actions checks and tests
├── backend/              # FastAPI backend
│   ├── main.py           # Application entry point
│   ├── ingestion/        # Kafka consumer services
│   ├── ml_service/       # Inference and alert engine
│   ├── db/               # TimescaleDB schema & seeds
│   └── tests/            # API & ML reliability test suite
├── frontend/             # React (Vite) frontend application
│   ├── src/components/   # Reusable UI components
│   ├── src/pages/        # Dashboard, Equipment, Work Orders
│   └── src/api/          # Backend API services
├── ml/                   # Machine learning pipelines
│   ├── artifacts/        # Trained models & configurations
│   ├── data_prep/        # Data extraction and pre-processing
│   └── models/           # Training scripts & definitions
├── simulator/            # Python-based equipment sensor simulator
│   ├── sensor_simulator.py
│   └── wait_for_kafka.py
├── infra/                # Infrastructure definitions
│   ├── docker-compose.yml 
│   └── airflow/          # Airflow DAGs for ML retraining pipeline
├── scripts/              # Utility scripts for CI and testing
│   └── docker_smoke_test.py
├── docs/                 # System documentation & runbooks
│   └── grafana/          # Grafana dashboard JSON models
└── data/                 # Local data directory (ignored in git)
    ├── raw/              
    └── processed/        
```

## 📊 Datasets

| Dataset | Purpose | Source |
|---------|---------|--------|
| NASA CMAPSS | RUL prediction (Remaining Useful Life) | [NASA Data](https://data.nasa.gov/dataset/CMAPSS-Jet-Engine-Simulated-Data/) |
| SECOM | Anomaly detection in manufacturing | [UCI ML Repository](https://archive.ics.uci.edu/ml/datasets/SECOM) |

## 📋 Equipment Monitored

- Granulation Line (`GRAN-LINE-01`)
- Tablet Press (`TABLET-PRESS-01`)
- Blister Packer (`BLISTER-PACK-01`)
- Capsule Filler (`CAPSULE-FILL-01`)
- Coating Machine (`COATING-DRUM-01`)
- Vial Washer (`VIAL-WASHER-01`)
- Aseptic Filler (`ASEPTIC-FILL-01`)
- CIP Skid (`CIP-SKID-01`)
- Ultra Low Freezer (`ULT-FREEZER-01`)
- Cold Room (`COLD-ROOM-01`)
- Chiller Loop (`CHILLER-LOOP-01`)
- Stability Chamber (`STABILITY-CHAMBER-01`)
- HPLC System (`HPLC-STACK-01`)
- LC-MS (`LCMS-01`)
- Dissolution Tester (`DISSOLUTION-01`)
- TOC Analyzer (`TOC-ANALYZER-01`)
- Infusion Pump (`INFUSION-PUMP-01`)
- Syringe Pump (`SYRINGE-PUMP-01`)
- Linear Accelerator (`LINAC-01`)
- CT Scanner (`CT-SCANNER-01`)

## ⚠️ Risk Levels And Actions

| Risk level | Trigger pattern | Action taken by system |
|-----------|-----------------|------------------------|
| `stable` | Low anomaly and low failure probability | Continue standard preventive maintenance |
| `watch` | Early drift signals | Increase monitoring frequency and verify calibration |
| `warning` | Moderate risk (`fp > 0.40` or equivalent) | Schedule maintenance in next window and watch trends |
| `high` | Escalating multi-signal risk | Urgent engineering review in current shift |
| `critical` | Severe risk (`fp > 0.80`, high anomaly, or near-failure horizon) | Create/refresh critical work order and require immediate inspection |

The API now returns `risk_level`, `risk_reason`, and `recommended_action` for each equipment item to support full presentation walkthroughs.
