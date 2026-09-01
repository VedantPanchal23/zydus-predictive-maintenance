# Product Requirements Document (PRD)
## Enterprise AI Predictive Maintenance & Asset Reliability Platform (Zydus-PdM)

---

## 1. Executive Summary & Problem Context

### 1.1 Business Context: Why This System Exists
**Zydus Lifesciences (Zydus Pharma)** operates world-class pharmaceutical manufacturing sites, analytical QC testing laboratories, automated cold-chain storage networks, and oncology clinical care facilities. In these environments, unplanned machine downtime, unnoticed sensor drift, and equipment failure lead to severe financial, operational, and regulatory consequences:

1. **Catastrophic Batch Loss in Sterile Injectables & Oncology Formulations**:
   - Equipment such as Granulation Lines, High-Speed Rotary Tablet Presses, Coating Drums, Aseptic Vial Filling Lines, and Clean-in-Place (CIP) skids run continuous high-value batches.
   - An unplanned stoppage during an aseptic filling or freeze-drying run invalidates the entire sterile batch, causing direct financial losses ranging from **$500,000 to $2,500,000 per incident**.

2. **Cold-Chain Degradation & Regulatory Excursions**:
   - Oncology Active Pharmaceutical Ingredients (APIs), monoclonal antibodies (mAbs), and biologics must be preserved at continuous ultra-low temperatures (-80°C to -20°C in Ultra-Low Freezers and Cold Rooms).
   - Undetected compressor wear or refrigeration degradation causes temperature excursions. Invalidation of cold-chain audit trails violates **US FDA 21 CFR Part 211, WHO Good Distribution Practices (GDP), and EU Annex 1**.

3. **QC Laboratory Analysis Blockers**:
   - High-Performance Liquid Chromatography (HPLC), Liquid Chromatography-Mass Spectrometry (LC-MS), Total Organic Carbon (TOC) Analyzers, and Dissolution Testers are critical path assets for drug release testing.
   - Unforeseen pump seal failures, column overpressure, or detector drift halt release testing, creating supply chain backlogs.

4. **Clinical Radiation & Infusion Safety**:
   - Linear Accelerators (LINAC), CT Simulators, and Smart Infusion/Syringe Pumps directly deliver cancer therapy to patients.
   - Premature magnetron/klystron degradation in LINAC units or occlusion pressure failures in infusion pumps compromise patient safety and clinical treatment schedules.

### 1.2 Mission & Objective
The mission of **Zydus-PdM** is to transform maintenance from **reactive fire-fighting** and **rigid calendar-based preventive maintenance** into **autonomous, ML-driven condition-based predictive maintenance**. 

The platform continuously analyzes multi-sensor telemetric streams, calculates real-time multi-variate anomaly scores, forecasts Remaining Useful Life (RUL) and 30-day failure probabilities, automatically coordinates prioritized work orders with electronic signatures (21 CFR Part 11 compliant), and alerts engineers before failures manifest.

---

## 2. Target Personas & User Journeys

| Persona | Role | Primary Needs & Workflows | Key System Interfaces |
| :--- | :--- | :--- | :--- |
| **Plant Reliability Engineer** | Operational monitoring, root-cause investigation | Real-time sensor trends, anomaly alerts, degradation velocity, vibration/pressure analysis, diagnostic guidance. | Equipment Detail, Sensor Analytics, Prediction History |
| **Maintenance Lead / Supervisor** | Resource dispatch, work order management | Triage incoming critical/warning alerts, dispatch maintenance technicians, approve parts replacement, track MTTR. | Alerts Hub, Work Orders Kanban, Maintenance Scheduler |
| **QC Lab Operations Manager** | Analytical instrument uptime | Track HPLC/LCMS column pressure stability, UV detector health, schedule calibration before drift causes out-of-specification (OOS). | Lab Asset Health, Calibration Logs, Alert Dashboard |
| **GxP Compliance & Quality Auditor** | Regulatory oversight & compliance | Immutable audit logs, electronic signatures on completed maintenance, tamper-evident records, temperature excursion logs. | Compliance Audit Viewer, 21 CFR Part 11 Sign-off, Export PDF |
| **Plant Operations Director (VP/CXO)** | Strategic KPI tracking | Overall Equipment Effectiveness (OEE), Mean Time Between Failures (MTBF), Mean Time to Repair (MTTR), annualized cost savings. | Executive KPI Summary, Asset Health Heatmap |

---

## 3. Scope of Monitored Assets & Sensor Profiles

The platform monitors **20 specialized pharmaceutical & hospital oncology assets** across 5 distinct operational families:

### Monitored Assets
- **Manufacturing Lines (Plant A, B, C & Utilities)**: GRAN-LINE-01, TABLET-PRESS-01, BLISTER-PACK-01, CAPSULE-FILL-01, COATING-DRUM-01, VIAL-WASHER-01, ASEPTIC-FILL-01, CIP-SKID-01
- **Cold-Chain & Environmental Storage**: ULT-FREEZER-01, COLD-ROOM-01, CHILLER-LOOP-01, STABILITY-CHAMBER-01
- **QC Analytical Laboratories**: HPLC-STACK-01, LCMS-01, DISSOLUTION-01, TOC-ANALYZER-01
- **Care Delivery & Clinical Infusion**: INFUSION-PUMP-01, SYRINGE-PUMP-01
- **Radiation Oncology & Diagnostic Imaging**: LINAC-01, CT-SCANNER-01

### Telemetry Channels & Sensor Specifications
1. **manufacturing_line**:
   - ibration_hz (10.060.0 Hz) - Bearing condition & mechanical unbalance
   - 	emperature_c (35.075.0 °C) - Motor drive and gearbox thermal load
   - motor_current_a (5.030.0 A) - Mechanical load and torque resistance
   - pressure_bar (1.010.0 bar) - Pneumatic and hydraulic compression lines
   - 
otation_speed_rpm (500.03000.0 RPM) - Drive spindle velocity
2. **cold_storage**:
   - 	emperature_c (-25.0 to -15.0 °C or -80.0 °C for ULT) - Internal thermal chamber
   - humidity_percent (30.070.0 %) - Relative chamber moisture
   - compressor_load_percent (20.090.0 %) - Cooling duty cycle
   - door_open_count (0.05.0/window) - Thermal envelope breach frequency
   - power_consumption_kw (1.08.0 kW) - Compressor and condenser electrical draw
3. **lab_hplc**:
   - column_pressure_bar (50.0400.0 bar) - Stationary phase hydraulic backpressure
   - low_rate_ml_min (0.15.0 mL/min) - Quaternary pump delivery accuracy
   - 	emperature_c (25.060.0 °C) - Column compartment thermal regulation
   - 
un_time_min (0.0120.0 min) - Assay sequence duration
   - uv_signal_mau (0.02000.0 mAU) - Photodiode array / UV baseline stability
4. **infusion_pump**:
   - low_rate_ml_hr (1.0500.0 mL/hr) - Volumetric infusion rate
   - pressure_mmhg (10.0300.0 mmHg) - In-line catheter occlusion resistance
   - attery_level_percent (0.0100.0 %) - Battery backup reserve
   - occlusion_flag (0 / 1) - Digital pressure gate status
   - cycle_count (010,000) - Linear peristaltic finger actuations
5. **
adiation_unit**:
   - eam_current_ma (1.050.0 mA) - Electron gun emission rate
   - dose_rate_gy_min (0.010.0 Gy/min) - Ion chamber dosimetry output
   - cooling_temp_c (15.035.0 °C) - Deionized cooling loop temperature
   - rc_voltage_v (100.0500.0 V) - Magnetron pulsed high-voltage
   - pulse_count (0100,000) - Total radiation pulse accumulation

---

## 4. Functional Requirements (FR)

### FR 1: Industrial Multi-Protocol Ingestion & Ingestion Reliability
- **FR 1.1**: The platform MUST support streaming ingestion from Kafka (equipment.sensors.raw) and industrial protocols (MQTT / OPC-UA / Webhooks).
- **FR 1.2**: Ingested data MUST be validated against a strict schema (valid numeric bounds, timestamp non-future, valid equipment ID) before insertion into TimescaleDB.
- **FR 1.3**: The ingestion engine MUST implement micro-batching (execute_values), connection pooling, and automatic retry with exponential backoff.
- **FR 1.4**: Corrupt or malformed telemetry payloads MUST be routed to a Dead Letter Queue (equipment.sensors.dlq) with error metadata, preventing data loss or pipeline stalls.

### FR 2: Real-time Multi-Model Machine Learning Engine
- **FR 2.1 Anomaly Detection**:
  - Unsupervised multivariate outlier detection using Isolation Forest and a temporal PyTorch LSTM Autoencoder.
  - Generates normalized Anomaly Scores between 0.000 (nominal) and 1.000 (severe anomaly).
- **FR 2.2 Failure Risk & RUL Forecasting**:
  - Gradient-boosted tree regressors (XGBoost) predicting numerical Remaining Useful Life in operating days/hours.
  - Calibrated XGBoost classifiers predicting the binary probability of failure within 30 cycles/days.
  - Feature engineering extracting 30 rolling statistical metrics.
- **FR 2.3 Model Confidence & Explainability**:
  - Output confidence scoring based on model convergence and signal concordance.
  - Feature attribution (SHAP values) indicating which specific sensors triggered high-risk classifications.
- **FR 2.4 Continuous MLOps**:
  - Automated drift detection (Kolmogorov-Smirnov test and Population Stability Index - PSI) on incoming sensor features.
  - Airflow ETL pipeline for scheduled or drift-triggered retraining, registering approved model versions to MLflow Model Registry.

### FR 3: Intelligent Alert & Incident Automation Engine
- **FR 3.1 Severity Categorization**:
  - **CRITICAL**: Failure Probability >= 0.80 OR Anomaly Score >= 0.90 OR RUL <= 3.0 days.
  - **WARNING**: Failure Probability >= 0.40 OR RUL <= 14.0 days OR (Anomaly >= 0.85 AND Risk Signal).
- **FR 3.2 Flapping Prevention & Cooldown Logic**:
  - Enforce independent cooldown windows (e.g., 6 hours for Critical, 2 hours for Warning) to prevent alert storms.
  - Automatically suppress Warning alerts if an active Critical alert or open Critical Work Order already exists for the asset.
  - Discard predictions older than 10 minutes.
- **FR 3.3 Automated Work Order Generation**:
  - Automatically generate a high-priority Work Order in status 'open' upon detection of a verified Critical event.
  - Intelligently upsert existing open work orders by adjusting the predicted failure date if risk accelerates, preventing duplicate tickets.
- **FR 3.4 Multi-Channel Escalation**:
  - Publish real-time events to Kafka topics equipment.alerts.critical and equipment.alerts.warning.
  - Dispatch real-time WebSocket notifications and trigger external webhook dispatchers (Email, SMS, Slack, PagerDuty).

### FR 4: GxP & US FDA 21 CFR Part 11 Regulatory Compliance
- **FR 4.1 Immutable Audit Trails**:
  - Every system action (alert acknowledgment, work order completion, threshold change, manual calibration override, user login/logout) MUST create an append-only, tamper-evident audit record in PostgreSQL udit_logs storing user_id, ction, entity_type, entity_id, efore_state, fter_state, ip_address, and 	imestamp_utc.
- **FR 4.2 Electronic Signatures & Dual-Control**:
  - Completing a critical work order or modifying ML alarm thresholds MUST require a re-authentication prompt (electronic signature) and a mandatory 
eason_for_change justification field.

### FR 5: High-Performance Real-Time Web Platform
- **FR 5.1 Responsive Operator Dashboard**:
  - Real-time KPI summary (Total Assets, Healthy, Warning, Critical, Active Alerts, Open Work Orders, Average Plant Health Score).
  - Equipment grid with color-coded status badges, live sensor value feeds, and risk factor summaries.
- **FR 5.2 Deep-Dive Asset Diagnostics**:
  - Interactive multi-sensor trend charts (Recharts) with historical zoom and pan.
  - Predictive failure curve, anomaly score progression, and actionable maintenance recommendations.
- **FR 5.3 Filterable Operations Hub**:
  - Alerts queue with instant multi-status filtering (All, Critical, Warning, Acknowledged) and single-click acknowledgment.
  - Work Orders queue with priority tagging (Critical, High, Medium, Low) and lifecycle state transitions.
- **FR 5.4 Unified Operational Event Log**:
  - Real-time event stream integrating raw sensor logs, prediction events, alert triggers, and maintenance completions.

---

## 5. Non-Functional Requirements (NFR)

| Category | Metric | Requirement Specification |
| :--- | :--- | :--- |
| **Performance** | API Latency | 99th percentile REST response time < 150 ms under 200 concurrent requests. |
| **Performance** | Ingestion Throughput | Ingest >= 2,000 sensor readings/sec with < 2.0 s end-to-end latency to TimescaleDB. |
| **Performance** | WebSocket Broadcast | Live sensor & alert push delivered to all active clients within < 500 ms of calculation. |
| **Availability** | System Uptime | 99.9% uptime for core backend, ingestion, and database services. |
| **Scalability** | Asset Scaling | Horizontal scaling supporting from 20 to 1,000+ assets without architectural redesign. |
| **Security** | Authentication | Strong JWT tokens (HS256/RS256) with salted bcrypt/Argon2 password hashing; zero plain-text secrets. |
| **Security** | Authorization | Strict Role-Based Access Control (admin, engineer, viewer, auditor). |
| **Data Retention** | Time-Series Archiving| 90 days hot data in TimescaleDB hypertables; compressed continuous aggregates for 365+ days. |

---

## 6. Acceptance Criteria & Quality Gates

1. **ML Quality Gates**:
   - Failure Classifier: AUC-ROC >= 0.95, F1-Score >= 0.80, Accuracy >= 0.94.
   - Regressor RUL: RMSE <= 60 cycles with non-negative bounded predictions.
2. **System Health & Integration**:
   - Full automated end-to-end Docker smoke test reporting 0 failures.
   - Backend unit and API test suites reporting 100% pass rate.
   - Frontend production build, ESLint, and Vitest suite passing with 0 errors.
3. **Security Verification**:
   - Mutation endpoints strictly reject unauthenticated or viewer-role requests with HTTP 401/403.
   - All database connections use authenticated, pooled connections with isolated credentials.
