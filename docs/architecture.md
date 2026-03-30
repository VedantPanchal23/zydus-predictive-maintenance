# System Architecture — Zydus Pharma Oncology Predictive Maintenance

## High-Level Overview

```
┌─────────────┐     ┌──────────┐     ┌───────────────┐
│  20 Oncology │────▶│  Apache  │────▶│   FastAPI      │
│  Equipment   │     │  Kafka   │     │   Backend      │
│  (Sensors)   │     │          │     │                │
└─────────────┘     └──────────┘     └───────┬───────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
              ┌─────▼─────┐         ┌──────▼──────┐        ┌──────▼──────┐
              │ TimescaleDB│         │   Redis     │        │   ML Models │
              │ (Postgres) │         │  (Cache)    │        │ (scikit/    │
              │            │         │             │        │  XGBoost/   │
              └────────────┘         └─────────────┘        │  PyTorch)   │
                                                            └──────┬──────┘
                                                                   │
                                          ┌────────────────────────┤
                                          │                        │
                                   ┌──────▼──────┐         ┌──────▼──────┐
                                   │   MLflow    │         │   MinIO     │
                                   │  (Tracking) │         │  (Storage)  │
                                   └─────────────┘         └─────────────┘

              ┌─────────────┐         ┌─────────────┐
              │   React     │         │   Grafana   │
              │  Frontend   │         │  Dashboards │
              └─────────────┘         └─────────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| FastAPI Backend | 8000 | REST API + WebSocket |
| TimescaleDB | 5432 | Time-series + relational storage |
| Redis | 6379 | Caching + real-time pub/sub |
| Kafka | 9092 | Sensor data streaming |
| Zookeeper | 2181 | Kafka coordination |
| MinIO | 9000/9001 | Model artifact storage |
| Grafana | 3001 | Monitoring dashboards |
| MLflow | 5000 | ML experiment tracking |

## Data Flow

1. **Sensor Simulator** → generates realistic sensor data for 20 equipment units
2. **Kafka** → streams sensor readings in real-time
3. **FastAPI** → consumes Kafka, stores in TimescaleDB, runs ML inference
4. **ML Models** → detect anomalies + predict RUL (Remaining Useful Life)
5. **Alerts** → auto-generated when failure probability exceeds threshold
6. **Work Orders** → auto-created for high-risk equipment
7. **React Frontend** → displays dashboards, alerts, and work orders
8. **Grafana** → real-time monitoring and historical trends

## Database Tables

- `equipment` — 20 oncology equipment units (master data)
- `sensor_readings` — TimescaleDB hypertable for time-series sensor data
- `predictions` — AI model prediction results
- `alerts` — System-generated alerts
- `work_orders` — Maintenance work orders

## ML Pipeline

- **Training Data**: NASA CMAPSS (RUL prediction) + SECOM (anomaly detection)
- **Models**: scikit-learn, XGBoost, PyTorch
- **Tracking**: MLflow for experiment management
- **Storage**: MinIO for model artifacts
