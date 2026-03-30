-- ============================================================
-- Zydus Pharma Oncology — Predictive Maintenance System
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
    anomaly_score FLOAT,
    failure_probability FLOAT,
    days_to_failure FLOAT,
    confidence FLOAT,
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

-- ============================================================
-- Seed 20 equipment rows (5 types × 3–5 units each)
-- ============================================================
INSERT INTO equipment (name, type, location, install_date, last_maintenance_date) VALUES
('MFG-LINE-01', 'manufacturing_line', 'Plant A - Floor 1', '2021-01-15', '2024-11-01'),
('MFG-LINE-02', 'manufacturing_line', 'Plant A - Floor 1', '2021-03-20', '2024-10-15'),
('MFG-LINE-03', 'manufacturing_line', 'Plant A - Floor 2', '2021-06-10', '2024-12-01'),
('MFG-LINE-04', 'manufacturing_line', 'Plant B - Floor 1', '2022-01-05', '2024-11-20'),
('MFG-LINE-05', 'manufacturing_line', 'Plant B - Floor 2', '2022-04-18', '2024-10-30'),
('COLD-UNIT-01', 'cold_storage', 'Storage Room A', '2020-08-12', '2024-12-10'),
('COLD-UNIT-02', 'cold_storage', 'Storage Room A', '2020-09-25', '2024-11-05'),
('COLD-UNIT-03', 'cold_storage', 'Storage Room B', '2021-02-14', '2024-10-20'),
('COLD-UNIT-04', 'cold_storage', 'Storage Room B', '2021-11-30', '2024-12-15'),
('LAB-HPLC-01', 'lab_hplc', 'Lab Block 1', '2022-03-08', '2024-11-25'),
('LAB-HPLC-02', 'lab_hplc', 'Lab Block 1', '2022-07-19', '2024-10-10'),
('LAB-HPLC-03', 'lab_hplc', 'Lab Block 2', '2023-01-22', '2024-12-05'),
('LAB-HPLC-04', 'lab_hplc', 'Lab Block 2', '2023-05-30', '2024-11-15'),
('INF-PUMP-01', 'infusion_pump', 'Oncology Ward 1', '2021-09-14', '2024-12-01'),
('INF-PUMP-02', 'infusion_pump', 'Oncology Ward 1', '2021-10-28', '2024-11-10'),
('INF-PUMP-03', 'infusion_pump', 'Oncology Ward 2', '2022-02-17', '2024-10-25'),
('INF-PUMP-04', 'infusion_pump', 'Oncology Ward 2', '2022-08-05', '2024-12-20'),
('RAD-UNIT-01', 'radiation_unit', 'Radiation Block', '2020-05-20', '2024-11-30'),
('RAD-UNIT-02', 'radiation_unit', 'Radiation Block', '2020-11-11', '2024-10-15'),
('RAD-UNIT-03', 'radiation_unit', 'Radiation Block', '2021-07-03', '2024-12-08');
