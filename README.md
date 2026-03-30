# 🏭 Zydus Pharma Oncology — AI Predictive Maintenance System

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

### 1. Start all services
```bash
cd infra
docker-compose up -d
```

### 2. Verify services
```bash
docker-compose ps
```

All 8 services should show as **healthy**.

### 3. Access services

| Service | URL |
|---------|-----|
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| MLflow | http://localhost:5000 |
| MinIO Console | http://localhost:9001 |

### 4. Prepare ML datasets
```bash
pip install pandas numpy scikit-learn pyarrow
python ml/data_prep/prepare_all.py
```

## 📁 Project Structure

```
zydus-predictive-maintenance/
├── backend/              # FastAPI backend
│   ├── main.py           # Application entry point
│   ├── requirements.txt  # Python dependencies
│   ├── Dockerfile        # Backend container
│   └── db/
│       └── schema.sql    # TimescaleDB schema + seed data
├── frontend/             # React frontend (Sprint 2+)
├── ml/                   # Machine learning
│   └── data_prep/
│       └── prepare_all.py  # Dataset preparation
├── simulator/            # Sensor data simulator
│   └── sensor_simulator.py
├── infra/                # Infrastructure
│   └── docker-compose.yml
├── data/
│   ├── raw/              # Raw datasets (not in git)
│   └── processed/        # Processed parquet files (not in git)
└── docs/
    └── architecture.md   # System architecture
```

## 📊 Datasets

| Dataset | Purpose | Source |
|---------|---------|--------|
| NASA CMAPSS | RUL prediction (Remaining Useful Life) | [NASA Data](https://data.nasa.gov/dataset/CMAPSS-Jet-Engine-Simulated-Data/) |
| SECOM | Anomaly detection in manufacturing | [UCI ML Repository](https://archive.ics.uci.edu/ml/datasets/SECOM) |

## 📋 Equipment Monitored

- 5× Drug Manufacturing Lines (MFG-LINE-01 to 05)
- 4× Cold Storage Units (COLD-UNIT-01 to 04)
- 4× Lab HPLC Machines (LAB-HPLC-01 to 04)
- 4× Infusion Pumps (INF-PUMP-01 to 04)
- 3× Radiation Units (RAD-UNIT-01 to 03)

## 📄 License

Proprietary — Zydus Pharma Oncology Pvt. Ltd.