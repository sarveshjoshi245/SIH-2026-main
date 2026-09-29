-- =============================================================================
-- PostgreSQL Database Setup: electricity_department
-- State Electricity Distribution Department API (Discom Simulator)
-- =============================================================================

-- 1. Create Tables

-- Electricity Applications Table
CREATE TABLE IF NOT EXISTS electricity_applications (
    id SERIAL PRIMARY KEY,
    application_number VARCHAR(50) UNIQUE NOT NULL,
    consumer_number VARCHAR(50),
    applicant_name VARCHAR(255) NOT NULL,
    applicant_pan VARCHAR(20) NOT NULL,
    premises_address TEXT NOT NULL,
    district VARCHAR(100) NOT NULL,
    taluka VARCHAR(100) NOT NULL,
    village VARCHAR(100) NOT NULL,
    supply_category VARCHAR(50) NOT NULL,
    connection_type VARCHAR(50) NOT NULL,
    requested_load VARCHAR(50) NOT NULL,
    requested_load_unit VARCHAR(20) NOT NULL DEFAULT 'KW',
    sanctioned_load VARCHAR(50) NOT NULL,
    sanctioned_load_unit VARCHAR(20) NOT NULL DEFAULT 'KW',
    application_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    inspection_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    meter_status VARCHAR(50) NOT NULL DEFAULT 'NOT_INSTALLED',
    connection_status VARCHAR(50) NOT NULL DEFAULT 'NOT_CONNECTED',
    outstanding_dues BOOLEAN NOT NULL DEFAULT FALSE,
    security_deposit_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    application_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rejection_reason TEXT,
    objection_reason TEXT,
    inspection_reference VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_elec_app_no ON electricity_applications(application_number);
CREATE INDEX IF NOT EXISTS idx_elec_app_pan ON electricity_applications(applicant_pan);
CREATE INDEX IF NOT EXISTS idx_elec_cons_no ON electricity_applications(consumer_number);

-- Electricity Connections Table
CREATE TABLE IF NOT EXISTS electricity_connections (
    id SERIAL PRIMARY KEY,
    consumer_number VARCHAR(50) UNIQUE NOT NULL,
    application_number VARCHAR(50),
    applicant_name VARCHAR(255) NOT NULL,
    applicant_pan VARCHAR(20) NOT NULL,
    premises_address TEXT NOT NULL,
    supply_category VARCHAR(50) NOT NULL,
    connection_type VARCHAR(50) NOT NULL,
    sanctioned_load VARCHAR(50) NOT NULL,
    sanctioned_load_unit VARCHAR(20) NOT NULL DEFAULT 'KW',
    meter_number VARCHAR(50),
    meter_status VARCHAR(50) NOT NULL DEFAULT 'INSTALLED',
    connection_status VARCHAR(50) NOT NULL DEFAULT 'ENERGIZED',
    outstanding_dues BOOLEAN NOT NULL DEFAULT FALSE,
    energization_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_elec_conn_no ON electricity_connections(consumer_number);
CREATE INDEX IF NOT EXISTS idx_elec_conn_pan ON electricity_connections(applicant_pan);

-- API Consumers Table (Machine-to-Machine API Keys and Scopes)
CREATE TABLE IF NOT EXISTS api_consumers (
    id SERIAL PRIMARY KEY,
    consumer_id VARCHAR(100) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_scopes TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_consumers_key ON api_consumers(api_key);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    transaction_id VARCHAR(100) NOT NULL,
    consumer_id VARCHAR(100),
    endpoint VARCHAR(255) NOT NULL,
    application_number VARCHAR(100),
    outcome VARCHAR(50) NOT NULL,
    response_code INTEGER NOT NULL,
    response_time_ms DOUBLE PRECISION NOT NULL,
    failure_type VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_elec_audit_time ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_elec_audit_txid ON audit_logs(transaction_id);

-- =============================================================================
-- 2. Seed Initial Data
-- =============================================================================

-- Seed API Consumers
INSERT INTO api_consumers (consumer_id, api_key, is_active, allowed_scopes)
VALUES
    ('INTEROP-PLATFORM', 'elec_live_interop_key_991', TRUE, '["/api/electricity/*", "/api/audit"]'),
    ('INDUSTRIAL-CLEARANCE', 'elec_live_clearance_key_552', TRUE, '["/api/electricity/*"]'),
    ('DEMO-FRONTEND', 'elec_demo_key_101', TRUE, '["/api/electricity/*", "/api/admin/*", "/api/audit"]'),
    ('ADMIN-CLIENT', 'elec_admin_secret_key_888', TRUE, '["*"]')
ON CONFLICT (consumer_id) DO NOTHING;

-- Seed Electricity Applications
INSERT INTO electricity_applications (
    application_number, consumer_number, applicant_name, applicant_pan, premises_address,
    district, taluka, village, supply_category, connection_type, requested_load,
    requested_load_unit, sanctioned_load, sanctioned_load_unit, application_status,
    inspection_status, meter_status, connection_status, outstanding_dues,
    security_deposit_status, application_date, last_updated, inspection_reference
) VALUES
    ('ELEC-2026-00101', 'CONS-778899', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'Plot 42, MIDC Industrial Area Phase II, Chakan', 'Pune', 'Khed', 'Chakan',
     'HT-IND', 'INDUSTRIAL', '500', 'KW', '500', 'KW', 'APPROVED',
     'COMPLETED', 'INSTALLED', 'ENERGIZED', FALSE, 'PAID',
     '2026-07-10 09:30:00+00', '2026-08-20 14:30:00+00', 'INSP-PN-2026-0811'),

    ('ELEC-2026-00102', NULL, 'XYZ Manufacturing Pvt Ltd', 'FGHIJ5678K',
     'Survey No 108/2, Talegaon Industrial Zone', 'Pune', 'Maval', 'Talegaon Dabhade',
     'HT-IND', 'INDUSTRIAL', '750', 'KW', '750', 'KW', 'PENDING',
     'PENDING', 'NOT_INSTALLED', 'NOT_CONNECTED', FALSE, 'PENDING',
     '2026-08-15 10:00:00+00', '2026-08-15 10:00:00+00', NULL),

    ('ELEC-2026-00103', NULL, 'DEF Industries Pvt Ltd', 'LMNOP9012Q',
     'Sector 19, Waluj Industrial Area', 'Chhatrapati Sambhajinagar', 'Gangapur', 'Waluj',
     'HT-IND', 'INDUSTRIAL', '1000', 'KW', '800', 'KW', 'APPROVED',
     'COMPLETED', 'INSTALLED', 'NOT_CONNECTED', TRUE, 'PAID',
     '2026-07-22 11:15:00+00', '2026-08-25 16:45:00+00', 'INSP-CSN-2026-0399'),

    ('ELEC-2026-00104', NULL, 'RST Industries Pvt Ltd', 'RSTUV3456W',
     'Gat No 310, Kurkumbh Chemical Zone', 'Pune', 'Daund', 'Kurkumbh',
     'LT-IND', 'INDUSTRIAL', '300', 'KW', '300', 'KW', 'REJECTED',
     'FAILED', 'NOT_INSTALLED', 'NOT_CONNECTED', FALSE, 'NOT_REQUIRED',
     '2026-08-01 14:00:00+00', '2026-08-18 17:30:00+00', 'INSP-PN-2026-0922'),

    ('ELEC-2026-00105', 'CONS-552211', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'Gat 88, Ranjangaon Mega Industrial Park', 'Pune', 'Shirur', 'Ranjangaon',
     'LT-IND', 'INDUSTRIAL', '250', 'KW', '250', 'KW', 'APPROVED',
     'COMPLETED', 'INSTALLED', 'ENERGIZED', TRUE, 'PAID',
     '2026-06-05 10:00:00+00', '2026-07-12 12:00:00+00', 'INSP-PN-2026-0412'),

    ('ELEC-2026-00106', NULL, 'PQR Industries Pvt Ltd', 'PQRWX7890Y',
     'Plot B-14, Butibori Industrial Estate', 'Nagpur', 'Nagpur Rural', 'Butibori',
     'HT-IND', 'INDUSTRIAL', '600', 'KW', '600', 'KW', 'UNDER_INSPECTION',
     'IN_PROGRESS', 'NOT_INSTALLED', 'NOT_CONNECTED', FALSE, 'PAID',
     '2026-08-20 11:00:00+00', '2026-09-01 15:00:00+00', 'INSP-NG-2026-0104')
ON CONFLICT (application_number) DO NOTHING;

-- Seed Existing Connections
INSERT INTO electricity_connections (
    consumer_number, application_number, applicant_name, applicant_pan,
    premises_address, supply_category, connection_type, sanctioned_load,
    sanctioned_load_unit, meter_number, meter_status, connection_status,
    outstanding_dues, energization_date, last_updated
) VALUES
    ('CONS-778899', 'ELEC-2026-00101', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'Plot 42, MIDC Industrial Area Phase II, Chakan', 'HT-IND', 'INDUSTRIAL',
     '500', 'KW', 'MTR-881290', 'INSTALLED', 'ENERGIZED', FALSE,
     '2026-08-20 14:30:00+00', '2026-08-20 14:30:00+00'),

    ('CONS-552211', 'ELEC-2026-00105', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'Gat 88, Ranjangaon Mega Industrial Park', 'LT-IND', 'INDUSTRIAL',
     '250', 'KW', 'MTR-551122', 'INSTALLED', 'ENERGIZED', TRUE,
     '2026-07-12 12:00:00+00', '2026-07-12 12:00:00+00')
ON CONFLICT (consumer_number) DO NOTHING;
