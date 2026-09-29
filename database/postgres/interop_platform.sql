-- =============================================================================
-- PostgreSQL Database Setup: interop_platform
-- Government Interoperability Platform Gateway (SIH26129)
-- =============================================================================

-- 1. Create Tables

-- Users table (Enterprise Applicants, Admins, Auditors)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    organization_pan VARCHAR(20) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'APPLICANT',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_organization_pan ON users(organization_pan);

-- User Consents table (Explicit Departmental Access Permissions)
CREATE TABLE IF NOT EXISTS user_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_pan VARCHAR(20) NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    allowed_departments TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_id ON user_consents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_consents_pan ON user_consents(organization_pan);

-- Departments table (Connected Department Services)
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    base_url VARCHAR(255) NOT NULL,
    auth_header_name VARCHAR(50) NOT NULL DEFAULT 'X-API-Key',
    auth_token VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_departments_code ON departments(code);

-- Project Transactions (Orchestrated Clearance Runs)
CREATE TABLE IF NOT EXISTS project_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    organization_pan VARCHAR(20) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    overall_status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
    canonical_payload TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_project_transactions_txid ON project_transactions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_project_transactions_pan ON project_transactions(organization_pan);

-- Department Step Executions (Individual Department Calls in a Transaction)
CREATE TABLE IF NOT EXISTS department_step_executions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL,
    department_code VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    http_status_code INTEGER,
    response_time_ms DOUBLE PRECISION NOT NULL,
    raw_response TEXT,
    canonical_fragment TEXT,
    error_message TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dept_step_txid ON department_step_executions(transaction_id);

-- Platform Audit Logs (Tamper-Proof Audit Trail with Masked PANs)
CREATE TABLE IF NOT EXISTS platform_audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    transaction_id VARCHAR(100),
    actor_email VARCHAR(255),
    actor_role VARCHAR(50),
    masked_pan VARCHAR(20),
    endpoint VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    outcome VARCHAR(50) NOT NULL,
    response_code INTEGER NOT NULL,
    response_time_ms DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_platform_audit_timestamp ON platform_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_platform_audit_txid ON platform_audit_logs(transaction_id);

-- Schema Mapping Rules (Direct & Computed Rules for Legacy -> Canonical)
CREATE TABLE IF NOT EXISTS schema_mapping_rules (
    id SERIAL PRIMARY KEY,
    department_code VARCHAR(50) NOT NULL,
    source_field VARCHAR(100) NOT NULL,
    target_canonical_field VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL DEFAULT 'DIRECT',
    transformation_expression VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_schema_mapping_dept ON schema_mapping_rules(department_code);

-- Schema Drift Logs (AI-Detected Schema Drifts & Suggestions)
CREATE TABLE IF NOT EXISTS schema_drift_logs (
    id SERIAL PRIMARY KEY,
    department_code VARCHAR(50) NOT NULL,
    detected_field VARCHAR(100) NOT NULL,
    suggested_canonical_field VARCHAR(100),
    confidence_score DOUBLE PRECISION NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING_APPROVAL',
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_schema_drift_dept ON schema_drift_logs(department_code);

-- =============================================================================
-- 2. Seed Initial Data
-- =============================================================================

-- Seed Users (Passwords: 'SecretPass123', 'AdminSecret888', 'AuditorPass999')
INSERT INTO users (id, email, hashed_password, organization_name, organization_pan, role, is_active)
VALUES
    (1, 'applicant@abcindustries.com', '$2b$12$nv8y2A/CtsvOSzvnardoPe2ZPvveWldnmUrUUmX7g11UJV5xfwB3S', 'ABC Industries Pvt Ltd', 'ABCDE1234F', 'APPLICANT', TRUE),
    (2, 'applicant@xyzmfg.com', '$2b$12$nv8y2A/CtsvOSzvnardoPe2ZPvveWldnmUrUUmX7g11UJV5xfwB3S', 'XYZ Manufacturing Pvt Ltd', 'FGHIJ5678K', 'APPLICANT', TRUE),
    (3, 'admin@interop.gov.in', '$2b$12$9/dkIxYbmS1DhgwB3DiRP.jAv7EziQ4WPjAgQvhW5So3ot6MiKkyK', 'Government Interoperability Directorate', 'GOVAA0000A', 'GOVT_ADMIN', TRUE),
    (4, 'auditor@sih.gov.in', '$2b$12$AUI0cVnk4sMZbluZa64bSusCLFbJHyY0NpiM4GP58gDIU61UhYsRK', 'National Compliance & Audit Bureau', 'GOVAA0000B', 'AUDITOR', TRUE)
ON CONFLICT (email) DO NOTHING;

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- Seed Active Consents
INSERT INTO user_consents (user_id, organization_pan, purpose, allowed_departments, is_active, expires_at)
VALUES
    (1, 'ABCDE1234F', 'Industrial Manufacturing Plant Establishment Clearance', '["LAND", "ELECTRICITY", "POLLUTION"]', TRUE, CURRENT_TIMESTAMP + INTERVAL '365 days'),
    (2, 'FGHIJ5678K', 'Industrial Manufacturing Plant Establishment Clearance', '["LAND", "ELECTRICITY", "POLLUTION"]', TRUE, CURRENT_TIMESTAMP + INTERVAL '365 days')
ON CONFLICT DO NOTHING;

-- Seed Departments
INSERT INTO departments (code, name, base_url, auth_header_name, auth_token, is_active)
VALUES
    ('LAND', 'Land Records & Revenue Department', 'http://localhost:4000', 'X-API-Key', 'interop-demo-key-001', TRUE),
    ('ELECTRICITY', 'Electricity Distribution Department', 'http://localhost:8000', 'X-API-Key', 'elec_live_interop_key_991', TRUE),
    ('POLLUTION', 'State Pollution Control Board', 'http://localhost:4002', 'X-API-Key', 'interop-demo-key-001', TRUE)
ON CONFLICT (code) DO NOTHING;

-- Seed Schema Mapping Rules
INSERT INTO schema_mapping_rules (department_code, source_field, target_canonical_field, rule_type)
VALUES
    ('LAND', 'gtn', 'land_records.survey_number', 'DIRECT'),
    ('LAND', 'malak_name', 'land_records.owner_name', 'DIRECT'),
    ('LAND', 'malak_pan', 'organization_pan', 'DIRECT'),
    ('LAND', 'kshetra', 'land_records.area_hectares', 'DIRECT'),
    ('LAND', 'jamabandi', 'land_records.status', 'DIRECT'),
    ('ELECTRICITY', 'appl_no', 'electricity_application.application_number', 'DIRECT'),
    ('ELECTRICITY', 'cust_pan', 'organization_pan', 'DIRECT'),
    ('ELECTRICITY', 'load_sanc', 'electricity_application.sanctioned_load_kw', 'DIRECT'),
    ('ELECTRICITY', 'appl_stat', 'electricity_application.status', 'DIRECT'),
    ('POLLUTION', 'application_no', 'pollution_clearance.application_number', 'DIRECT'),
    ('POLLUTION', 'industry_pan', 'organization_pan', 'DIRECT'),
    ('POLLUTION', 'consent_status', 'pollution_clearance.consent_status', 'DIRECT')
ON CONFLICT DO NOTHING;
