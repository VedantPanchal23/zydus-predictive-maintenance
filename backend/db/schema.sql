-- =============================================================================
-- ZYDUS PHARMA ONCOLOGY - PREDICTIVE MAINTENANCE & ASSET RELIABILITY DATABASE
-- TimescaleDB 16+ / PostgreSQL Schema with GxP & 21 CFR Part 11 Audit Trail
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. EQUIPMENT MASTER TABLE ---------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment (
    id SERIAL PRIMARY KEY,
    equipment_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    criticality VARCHAR(50) DEFAULT 'HIGH',
    facility VARCHAR(150) DEFAULT 'Zydus Oncology Complex',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SENSOR TELEMETRY HYPERTABLE ----------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL,
    equipment_id VARCHAR(50) NOT NULL,
    sensor_name VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL
);

SELECT create_hypertable('sensor_readings', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_eq_time ON sensor_readings (equipment_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_name ON sensor_readings (sensor_name, timestamp DESC);

-- 3. DEAD LETTER QUEUE (DLQ) TABLE --------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry_dlq (
    id BIGSERIAL PRIMARY KEY,
    equipment_id VARCHAR(50) NOT NULL,
    sensor_name VARCHAR(50),
    raw_payload JSONB NOT NULL,
    error_reason TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'kafka',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_dlq_created ON telemetry_dlq (created_at DESC);

-- 4. PREDICTIONS TABLE --------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    equipment_id VARCHAR(50) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    failure_probability DOUBLE PRECISION NOT NULL,
    days_to_failure DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    features_used JSONB DEFAULT '{}',
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_eq_time ON predictions (equipment_id, predicted_at DESC);

-- 5. ALERTS TABLE -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    equipment_id VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    anomaly_score DOUBLE PRECISION,
    failure_probability DOUBLE PRECISION,
    days_to_failure DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_eq ON alerts (equipment_id, created_at DESC);

-- 6. WORK ORDERS TABLE (WITH GXP SOP PRESCRIPTIONS) ---------------------------
CREATE TABLE IF NOT EXISTS work_orders (
    id BIGSERIAL PRIMARY KEY,
    equipment_id VARCHAR(50) NOT NULL,
    alert_id BIGINT,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    description TEXT NOT NULL,
    sop_code VARCHAR(50),
    sop_title VARCHAR(200),
    required_tooling JSONB DEFAULT '[]',
    cleanroom_ppe JSONB DEFAULT '[]',
    assigned_to VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    completed_by VARCHAR(100),
    completion_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_workorders_eq ON work_orders (equipment_id, status);

-- 7. USERS & RBAC CREDENTIALS TABLE -------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    full_name VARCHAR(150),
    email VARCHAR(150),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. GXP / 21 CFR PART 11 CRYPTOGRAPHIC AUDIT TRAIL TABLE ---------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    reason_for_change TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    previous_hash VARCHAR(64),
    record_hash VARCHAR(64) NOT NULL,
    timestamp_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs (user_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs (action, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs (entity_type, entity_id);

-- 9. SYSTEM CONFIGURATION TABLE -----------------------------------------------
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_by VARCHAR(100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SEED MASTER DATA
-- =============================================================================

INSERT INTO equipment (equipment_id, name, category, criticality, facility) VALUES
('GRAN-LINE-01', 'High Shear Mixer Granulator 600L', 'Granulation', 'CRITICAL', 'Oral Solid Dosage Block A'),
('FBD-DRYER-01', 'Fluid Bed Dryer FBD-300', 'Granulation', 'HIGH', 'Oral Solid Dosage Block A'),
('TAB-PRESS-01', 'Rotary Tablet Press 45-Station', 'Granulation', 'CRITICAL', 'Oral Solid Dosage Block A'),
('COATER-01', 'Auto-Coater Perforated Pan 150kg', 'Granulation', 'HIGH', 'Oral Solid Dosage Block A'),
('VIAL-FILL-01', 'Aseptic Vial Filling & Stoppering Line', 'Sterile Injectables', 'LIFE_CRITICAL', 'Sterile Injectable Complex B'),
('LYO-CHAMBER-01', 'Industrial Freeze Dryer Lyophilizer 50m²', 'Sterile Injectables', 'LIFE_CRITICAL', 'Sterile Injectable Complex B'),
('AUTOCLAVE-01', 'Porous Load Steam Sterilizer 2000L', 'Sterile Injectables', 'CRITICAL', 'Sterile Injectable Complex B'),
('WFI-STILL-01', 'Multiple Effect WFI Generation Still', 'Sterile Injectables', 'LIFE_CRITICAL', 'Sterile Injectable Complex B'),
('BIOREACTOR-01', 'Single-Use Bioreactor 2000L', 'Bioprocessing', 'LIFE_CRITICAL', 'Biologics Pilot Plant C'),
('TFF-SKID-01', 'Tangential Flow Filtration Skid', 'Bioprocessing', 'CRITICAL', 'Biologics Pilot Plant C'),
('CHROM-SKID-01', 'Preparative Chromatography Skid', 'Bioprocessing', 'CRITICAL', 'Biologics Pilot Plant C'),
('CIP-SYSTEM-01', 'Clean-In-Place Recirculation Unit', 'Bioprocessing', 'HIGH', 'Biologics Pilot Plant C'),
('HPLC-AUTO-01', 'UPLC Quaternary Solvent Pump', 'Analytical Lab', 'HIGH', 'Central Quality Control Lab'),
('LCMS-CHAMBER-01', 'LC-MS/MS Triple Quadrupole Chamber', 'Analytical Lab', 'CRITICAL', 'Central Quality Control Lab'),
('SPECTRO-UV-01', 'UV-Vis Double Beam Spectrophotometer', 'Analytical Lab', 'MEDIUM', 'Central Quality Control Lab'),
('DISSOLUTION-01', 'Automated USP Dissolution Tester', 'Analytical Lab', 'HIGH', 'Central Quality Control Lab'),
('LINAC-01', 'Varian TrueBeam Linear Accelerator', 'Hospital Oncology', 'LIFE_CRITICAL', 'Zydus Comprehensive Cancer Center'),
('CYCLOTRON-01', 'Medical PET Radioisotope Cyclotron', 'Hospital Oncology', 'LIFE_CRITICAL', 'Zydus Comprehensive Cancer Center'),
('MRI-CRYO-01', '3T MRI Superconducting Cryocooler', 'Hospital Oncology', 'LIFE_CRITICAL', 'Zydus Comprehensive Cancer Center'),
('ULT-FREEZER-01', '-80°C Cryopreservation Biobank Vault', 'Hospital Oncology', 'LIFE_CRITICAL', 'Zydus Comprehensive Cancer Center')
ON CONFLICT (equipment_id) DO NOTHING;

-- Seed Default GxP Users with Salted Bcrypt Hashes (Password format: admin123, eng123, view123, audit123)
INSERT INTO users (username, hashed_password, role, full_name, email) VALUES
('admin', '$2b$12$zAumhxNoyCoyN.hNRoye0O.xjR6vLUIm61mO.bbRbiAAnNbz9kIBS', 'admin', 'System Administrator', 'admin@zydus.internal'),
('engineer1', '$2b$12$0F4OAbmuHrLScx3zrW8H7eT.VJ8hv8FWGYnTSeLrv.W4qFKkllziK', 'engineer', 'Lead Reliability Engineer', 'engineer1@zydus.internal'),
('viewer1', '$2b$12$LkHrq0ACaPpb/0RlooGiIOEyCG4divKRIyaRaTAlxNoVuCMLkeSDC', 'viewer', 'Operations Viewer', 'viewer1@zydus.internal'),
('auditor1', '$2b$12$mz/qz/vk0NIqWrdtSup6GOVxosLUGTMnHAwUu/ezswSjI.j4rofdC', 'auditor', 'GxP Quality Auditor', 'auditor1@zydus.internal')
ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;
