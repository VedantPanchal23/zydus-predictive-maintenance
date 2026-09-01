# Enterprise Production System Architecture
## Zydus Pharma Predictive Maintenance & Asset Reliability Platform (Zydus-PdM)
### Version 3.0  Advanced Clean Microservices Architecture

---

## 1. Executive Architectural Blueprint

The **Zydus-PdM** platform is an enterprise-grade, condition-based predictive maintenance and asset reliability system designed for high-stakes pharmaceutical manufacturing plants, QC analytical laboratories, cold-chain storage facilities, and hospital oncology environments.

```
+----------------------------------------------------------------------------------------------------------------+
¦                                       INDUSTRIAL EDGE & INGESTION LAYER                                        ¦
¦                                                                                                                ¦
¦   20 Monitored Pharma & Hospital Assets (PLCs / SCADA / IoT Sensors / Lab Analyzers)                           ¦
¦   Protocols: OPC-UA Gateway  |  MQTT (Sparkplug B)  |  HTTP Telemetry Ingest  |  Kafka Producer                ¦
¦                                              ¦                                                                 ¦
¦                                              ?                                                                 ¦
¦                          Apache Kafka Cluster (Confluent / KRaft)                                              ¦
¦                Topic: equipment.sensors.raw (Partitioned by Equipment ID)                                     ¦
¦                Topic: equipment.sensors.dlq (Dead Letter Queue with Error Metadata)                           ¦
¦                Topic: equipment.alerts.critical & equipment.alerts.warning                                    ¦
+----------------------------------------------------------------------------------------------------------------+
                                               ¦
                                               ?
+----------------------------------------------------------------------------------------------------------------+
¦                                        CORE ENGINE & STREAMING BACKEND                                         ¦
¦                                                                                                                ¦
¦   FastAPI High-Performance Async Gateway (Single Clean Cohesive Microservice)                                  ¦
¦   +-- Ingestion Engine        : Micro-batching (`execute_values`), DLQ error routing, Range validation         ¦
¦   +-- Storage Layer           : TimescaleDB 15 Hypertables + Continuous Aggregates (1-min / 1-hour)            ¦
¦   +-- Connection Pool         : Thread-Safe `ThreadedConnectionPool` with circuit breaker & auto-reconnect     ¦
¦   +-- ML Inference Pipeline   : Multi-Model Ensemble (IF + LSTM Autoencoder + XGBoost Reg & Class)             ¦
¦   +-- Model Explainability    : Real-Time Feature Attribution (SHAP / Residual Contribution per Sensor)        ¦
¦   +-- Drift Detection Monitor : Rolling Kolmogorov-Smirnov & Population Stability Index (PSI)                  ¦
¦   +-- Incident State Machine  : Hysteresis-filtered Alert Engine + Automated Critical Work Orders               ¦
¦   +-- Compliance & Security   : US FDA 21 CFR Part 11 Cryptographic SHA-256 Chained Audit Trail + 4-Tier RBAC ¦
¦   +-- Real-Time Streaming    : Redis Pub/Sub Backbone + Async WebSocket Broadcaster Hub                        ¦
+----------------------------------------------------------------------------------------------------------------+
                                               ¦
                                               ?
+----------------------------------------------------------------------------------------------------------------+
¦                                         STORAGE, STATE & OBSERVABILITY                                         ¦
¦                                                                                                                ¦
¦  +-------------------------------+ +-------------------------------+ +--------------------------------------+  ¦
¦  ¦   TimescaleDB (Postgres 15)   ¦ ¦            Redis 7            ¦ ¦             Grafana 12.0             ¦  ¦
¦  ¦  sensor_readings hypertable  ¦ ¦  pred:{equipment_id} cache   ¦ ¦  Provisioned Executive Dashboards   ¦  ¦
¦  ¦  1-min & 1-hour aggregates   ¦ ¦  Pub/Sub Broadcast Channels  ¦ ¦  Real-Time TimescaleDB Queries      ¦  ¦
¦  ¦  21 CFR Part 11 audit_logs   ¦ ¦  Rate Limiting & Auth State  ¦ ¦  Sensor Trends & Anomaly Residuals  ¦  ¦
¦  ¦  equipment, alerts, orders   ¦ ¦  DLQ Retry Buffers           ¦ ¦  System Health & Ingestion Rate     ¦  ¦
¦  +-------------------------------+ +-------------------------------+ +--------------------------------------+  ¦
+----------------------------------------------------------------------------------------------------------------+
```

---

## 2. Component Design & Clean Architecture Patterns

The backend follows **Clean Architecture & Domain-Driven Design (DDD)** principles, structured into modular bounded contexts:

```
backend/
+-- core/                  # Cross-cutting infrastructure: Config, DB Pool, Crypto Audit, Security
¦   +-- config.py          # Centralized typed configuration
¦   +-- db_pool.py         # Thread-safe pooled connection manager with circuit breaker
¦   +-- audit_logger.py    # 21 CFR Part 11 SHA-256 hash-chained audit logger
¦   +-- crypto_chain.py    # Tamper-evident cryptographic verification helpers
¦   +-- reliability.py     # Exponential backoff retry policies
¦
+-- domain/                # Enterprise domain models, enums & value objects
¦   +-- equipment.py       # Equipment profiles, sensor definitions & physical bounds
¦   +-- telemetry.py       # Telemetry models, validation schemas & units
¦   +-- prediction.py      # Inference output schemas & explainability attribution
¦   +-- alert.py           # Alert severities, work order states & SLA models
¦
+-- ingestion/             # Multi-protocol ingestion & telemetry validation
¦   +-- kafka_consumer.py  # High-throughput batch Kafka consumer
¦   +-- webhook_ingest.py  # HTTP telemetry ingestion endpoint
¦   +-- validator.py       # Sensor range, timestamp & schema validator
¦   +-- dlq.py             # Dead Letter Queue router & error tracker
¦
+-- ml/                    # Machine learning core & real-time analytics
¦   +-- inference.py       # Multi-model inference (IF, PyTorch LSTM, XGBoost)
¦   +-- explainability.py  # Feature attribution & root-cause residual diagnostics
¦   +-- drift_monitor.py   # Statistical drift detector (KS-Test & PSI)
¦   +-- scheduler.py       # Background condition monitoring loop
¦   +-- model_loader.py    # Model artifact loader with checksum verification
¦
+-- incident/              # Incident management & regulatory automation
¦   +-- state_machine.py   # Hysteresis-filtered alert state machine (NORMAL/WATCH/WARNING/CRITICAL)
¦   +-- alert_engine.py    # Multi-signal alert evaluator & cooldown deduplicator
¦   +-- workorder_manager.py # Auto work order generation, priority escalation & sign-offs
¦
+-- streaming/             # Real-time event streaming & push infrastructure
¦   +-- redis_bus.py       # Redis Pub/Sub event bus
¦   +-- ws_broadcaster.py  # Decoupled high-concurrency WebSocket hub
¦
+-- api/                   # Presentation & REST API layer
    +-- routes_auth.py     # Database-backed JWT auth & user administration
    +-- routes_equipment.py# Equipment directory, sensor history & diagnostics
    +-- routes_alerts.py   # Alert hub & acknowledgment workflows
    +-- routes_workorders.py # Maintenance work order lifecycle & completion
    +-- routes_audit.py    # GxP compliance audit trail viewer & verification
    +-- routes_metrics.py  # Prometheus `/metrics` and Kubernetes `/health` probes
    +-- main.py            # Clean FastAPI application entrypoint with lifespan manager
```

---

## 3. Storage Architecture & TimescaleDB Optimization

### 3.1 Partitioning & Continuous Aggregates
- **Raw Telemetry**: `sensor_readings` hypertable partitioned in 1-day chunks indexed by `(equipment_id, timestamp DESC)`.
- **Continuous Aggregates (Materialized Views)**:
  - `sensor_readings_1min`: Automatically rolled up by TimescaleDB background workers computing `avg`, `min`, `max`, `stddev` per minute.
  - Queries for multi-day sensor charts read directly from `sensor_readings_1min`, executing in **< 5ms** instead of scanning millions of rows.
- **Compression & Data Lifecycle**:
  - Chunks older than **7 days** compressed with column-oriented compression (90%+ storage savings).
  - Raw chunks dropped after **90 days**; aggregated trends retained for **10 years** for GxP compliance.

### 3.2 Thread-Safe Database Pooling
- Dedicated `ThreadedConnectionPool` (2 to 30 connections) with statement timeout protection (`statement_timeout = '10s'`) and automatic connection health verification.

---

## 4. Multi-Model ML Ensemble & Real-Time Explainability

```
                               +--------------------------------+
                               ¦ Aligned Multi-Channel Telemetry¦
                               +--------------------------------+
                                               ¦
                    +--------------------------+--------------------------+
                    ?                          ?                          ?
        +-----------------------+  +-----------------------+  +-----------------------+
        ¦   Isolation Forest    ¦  ¦   LSTM Autoencoder    ¦  ¦ XGBoost Reg & Class   ¦
        ¦ Multivariate Outlier  ¦  ¦ Temporal Reconstruct. ¦  ¦ RUL (Days) + P(Fail)  ¦
        +-----------------------+  +-----------------------+  +-----------------------+
                    ¦                          ¦                          ¦
                    +--------------------------+--------------------------+
                                               ¦
                                               ?
                               +--------------------------------+
                               ¦ Ensemble Calibration Scorer    ¦
                               +--------------------------------+
                                               ¦
                    +-----------------------------------------------------+
                    ?                                                     ?
        +-----------------------+                             +-----------------------+
        ¦ Feature Attribution   ¦                             ¦ Data Drift Monitor    ¦
        ¦ (Per-Sensor Residuals)¦                             ¦ (KS-Test & PSI Index) ¦
        +-----------------------+                             +-----------------------+
```

### 4.1 Feature Attribution (Explainability Diagnostics)
When an asset enters a high-risk state, the engine calculates the normalized contribution of each sensor:
$$\text{Contribution}_i = \frac{|x_i - \mu_i|}{\sigma_i + \epsilon} \cdot w_i$$
This outputs actionable diagnostic metadata:
`{"top_contributors": [{"sensor": "vibration_hz", "impact": 0.48}, {"sensor": "temperature_c", "impact": 0.35}]}`.

### 4.2 Automated Data Drift Detection
Rolling 1,000 sensor observations are compared against baseline training distributions using the **Population Stability Index (PSI)**:
$$\text{PSI} = \sum \left( P_i - Q_i \right) \ln\left(\frac{P_i}{Q_i}\right)$$
If $\text{PSI} > 0.25$, the system flags significant data drift, logging an audit record and notifying ML engineers to trigger retraining.

---

## 5. Incident Lifecycle & 21 CFR Part 11 Compliance

### 5.1 Hysteresis-Filtered Alert State Machine
```
   +----------+   3 consecutive breaches   +---------+   3 consecutive breaches   +----------+
   ¦  NORMAL  ¦ -------------------------? ¦ WARNING ¦ -------------------------? ¦ CRITICAL ¦
   +----------+                            +---------+                            +----------+
        ?                                       ¦                                      ¦
        ¦           5 consecutive healthy       ¦                5 consecutive healthy ¦
        +------------------------------------------------------------------------------+
```

### 5.2 SHA-256 Hash-Chained Immutable Audit Trail
Every state change creates an audit record cryptographically linked to the prior record:
$$\text{RecordHash}_k = \text{SHA256}\left(\text{RecordHash}_{k-1} \,\|\, \text{user\_id} \,\|\, \text{action} \,\|\, \text{payload} \,\|\, \text{ts}\right)$$
This provides mathematical proof of tamper resistance during regulatory audits.

---

## 6. Observability, Metrics & Production Health Probes

- **`/health/live`**: Liveness probe confirming process is active.
- **`/health/ready`**: Readiness probe verifying PostgreSQL, Redis, and Kafka connectivity.
- **`/metrics`**: Prometheus metrics exposing:
  - `pdm_telemetry_ingest_total`: Total sensor readings ingested.
  - `pdm_inference_latency_seconds`: ML inference latency histogram.
  - `pdm_active_websocket_connections`: Number of live connected clients.
  - `pdm_db_pool_active_connections`: Current connection pool utilization.
