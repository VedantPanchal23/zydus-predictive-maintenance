-- ============================================================
-- Zydus Pharma Oncology - Predictive Maintenance System
-- Database Schema (TimescaleDB + PostgreSQL 15)
-- ============================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Equipment master table
CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    install_date DATE,
    last_maintenance_date DATE,
    status VARCHAR(20) DEFAULT 'active'
);

-- Sensor readings (will become TimescaleDB hypertable)
CREATE TABLE sensor_readings (
    id BIGSERIAL,
    equipment_id INTEGER REFERENCES equipment(id),
    sensor_name VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AI predictions
CREATE TABLE predictions (
    id BIGSERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    anomaly_score FLOAT CHECK (anomaly_score IS NULL OR (anomaly_score >= 0 AND anomaly_score <= 1)),
    failure_probability FLOAT CHECK (failure_probability IS NULL OR (failure_probability >= 0 AND failure_probability <= 1)),
    days_to_failure FLOAT CHECK (days_to_failure IS NULL OR days_to_failure >= 0),
    confidence FLOAT CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    predicted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ
);

-- Work orders
CREATE TABLE work_orders (
    id BIGSERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    priority VARCHAR(20),
    description TEXT,
    predicted_failure_date DATE,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Convert sensor_readings to hypertable
SELECT create_hypertable('sensor_readings', 'timestamp');

-- Query performance for live dashboards and API pages
CREATE UNIQUE INDEX IF NOT EXISTS idx_equipment_name_unique ON equipment (name);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_equipment_time
    ON sensor_readings (equipment_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_time
    ON sensor_readings (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_equipment_time
    ON predictions (equipment_id, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_open_created
    ON alerts (created_at DESC) WHERE acknowledged_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_orders_status_priority
    ON work_orders (status, priority);

-- ============================================================
-- Seed 20 equipment rows (20 presentation-ready equipment categories)
-- ============================================================
INSERT INTO equipment (name, type, location, install_date, last_maintenance_date) VALUES
('GRAN-LINE-01', 'granulation_line', 'Plant A - Granulation Bay', '2021-01-15', '2026-03-12'),
('TABLET-PRESS-01', 'tablet_press', 'Plant A - Compression Suite', '2021-03-20', '2026-03-05'),
('BLISTER-PACK-01', 'blister_packer', 'Plant A - Packaging Cell', '2021-06-10', '2026-03-21'),
('CAPSULE-FILL-01', 'capsule_filler', 'Plant B - Capsule Suite', '2022-01-05', '2026-03-15'),
('COATING-DRUM-01', 'coating_machine', 'Plant B - Coating Room', '2022-04-18', '2026-03-09'),
('VIAL-WASHER-01', 'vial_washer', 'Plant C - Sterile Prep', '2022-08-02', '2026-03-07'),
('ASEPTIC-FILL-01', 'aseptic_filler', 'Plant C - Filling Line', '2023-02-16', '2026-03-13'),
('CIP-SKID-01', 'cip_skid', 'Utilities - CIP Zone', '2023-06-01', '2026-03-10'),
('ULT-FREEZER-01', 'ultra_low_freezer', 'Cold Chain Room A', '2020-08-12', '2026-03-18'),
('COLD-ROOM-01', 'cold_room', 'Cold Chain Room B', '2020-09-25', '2026-03-02'),
('CHILLER-LOOP-01', 'chiller_loop', 'Utilities - Chiller Deck', '2021-02-14', '2026-03-14'),
('STABILITY-CHAMBER-01', 'stability_chamber', 'QC Stability Lab', '2021-11-30', '2026-03-19'),
('HPLC-STACK-01', 'hplc_system', 'QC Lab Block 1', '2022-03-08', '2026-03-08'),
('LCMS-01', 'lc_ms', 'QC Lab Block 1', '2022-07-19', '2026-03-20'),
('DISSOLUTION-01', 'dissolution_tester', 'QC Lab Block 2', '2023-01-22', '2026-03-06'),
('TOC-ANALYZER-01', 'toc_analyzer', 'Water Quality Lab', '2023-05-30', '2026-03-11'),
('INFUSION-PUMP-01', 'infusion_pump', 'Oncology Ward 1', '2021-09-14', '2026-03-16'),
('SYRINGE-PUMP-01', 'syringe_pump', 'Oncology Ward 2', '2022-02-17', '2026-03-17'),
('LINAC-01', 'linear_accelerator', 'Radiation Therapy Block', '2020-05-20', '2026-03-22'),
('CT-SCANNER-01', 'ct_scanner', 'Imaging Center', '2021-07-03', '2026-03-04');
