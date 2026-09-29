-- =============================================================================
-- PostgreSQL Database Setup: Department Records (Land & Pollution)
-- Can be executed in 'interop_platform' or a dedicated departmental schema
-- =============================================================================

-- 1. Land Records Table
CREATE TABLE IF NOT EXISTS land_records (
    id SERIAL PRIMARY KEY,
    gtn VARCHAR(50) UNIQUE NOT NULL,               -- Survey / Gat Number
    malak_name VARCHAR(255) NOT NULL,              -- Owner Name
    malak_pan VARCHAR(20) NOT NULL,                -- Owner PAN
    kshetra VARCHAR(20) NOT NULL,                  -- Land Area
    kshetra_unit VARCHAR(20) NOT NULL DEFAULT 'HA',-- Area Unit (Hectare)
    jamabandi VARCHAR(50) NOT NULL,                -- Mutation Status (APPROVED, PENDING, REJECTED)
    jamin_prakar VARCHAR(50) NOT NULL,             -- Land Type (INDUSTRIAL, AGRICULTURAL)
    bandhak BOOLEAN NOT NULL DEFAULT FALSE,        -- Encumbrance / Lien flag
    court_case BOOLEAN NOT NULL DEFAULT FALSE,     -- Litigation pending flag
    district VARCHAR(100) NOT NULL,
    taluka VARCHAR(100) NOT NULL,
    village VARCHAR(100) NOT NULL,
    simulate_outage BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_land_gtn ON land_records(gtn);
CREATE INDEX IF NOT EXISTS idx_land_pan ON land_records(malak_pan);

-- Seed Land Records
INSERT INTO land_records (gtn, malak_name, malak_pan, kshetra, kshetra_unit, jamabandi, jamin_prakar, bandhak, court_case, district, taluka, village, simulate_outage)
VALUES
    ('101', 'ABC Industries Pvt Ltd', 'ABCDE1234F', '8.0', 'HA', 'APPROVED', 'INDUSTRIAL', FALSE, FALSE, 'Pune', 'Haveli', 'Wagholi', FALSE),
    ('102', 'ABC Industries Pvt Ltd', 'ABCDE1234F', '12.5', 'HA', 'APPROVED', 'INDUSTRIAL', FALSE, FALSE, 'Pune', 'Haveli', 'Wagholi', FALSE),
    ('103', 'ABC Industries Pvt Ltd', 'ABCDE1234F', '6.2', 'HA', 'PENDING', 'INDUSTRIAL', FALSE, FALSE, 'Pune', 'Mulshi', 'Pirangut', FALSE),
    ('104', 'XYZ Textiles Ltd', 'XYZPT5678K', '4.0', 'HA', 'REJECTED', 'AGRICULTURAL', FALSE, FALSE, 'Nashik', 'Niphad', 'Lasalgaon', FALSE),
    ('105', 'Konkan Ventures LLP', 'KONVL9012M', '3.3', 'HA', 'APPROVED', 'INDUSTRIAL', TRUE, TRUE, 'Raigad', 'Panvel', 'Karanjade', FALSE),
    ('999', 'Demo Outage Corp', 'OUTAG0000Z', '1.0', 'HA', 'APPROVED', 'INDUSTRIAL', FALSE, FALSE, 'Pune', 'Haveli', 'Demo', TRUE)
ON CONFLICT (gtn) DO NOTHING;


-- 2. Pollution Applications Table (State Pollution Control Board - MPCB)
CREATE TABLE IF NOT EXISTS pollution_applications (
    id SERIAL PRIMARY KEY,
    application_no VARCHAR(50) UNIQUE NOT NULL,
    application_project_id VARCHAR(50),
    industry_name VARCHAR(255) NOT NULL,
    industry_pan VARCHAR(20) NOT NULL,
    plant_location VARCHAR(255) NOT NULL,
    region VARCHAR(100) NOT NULL,
    industry_type VARCHAR(100) NOT NULL,
    consent_type VARCHAR(20) NOT NULL,             -- CTE (Consent to Establish) / CTO (Consent to Operate)
    consent_status VARCHAR(50) NOT NULL,           -- APPROVED, PENDING, REJECTED, UNDER_OBJECTION
    valid_until DATE,
    compliance_status VARCHAR(50) NOT NULL,        -- COMPLIANT, UNDER_REVIEW, NON_COMPLIANT, ACTION_REQUIRED
    air_emission_category VARCHAR(20) NOT NULL,    -- RED, ORANGE, GREEN
    water_discharge_category VARCHAR(20) NOT NULL, -- HIGH, MEDIUM, LOW
    hazardous_waste BOOLEAN NOT NULL DEFAULT FALSE,
    environmental_clearance_required BOOLEAN NOT NULL DEFAULT FALSE,
    simulate_outage BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_poll_app_no ON pollution_applications(application_no);
CREATE INDEX IF NOT EXISTS idx_poll_pan ON pollution_applications(industry_pan);

-- Seed Pollution Records
INSERT INTO pollution_applications (
    application_no, application_project_id, industry_name, industry_pan,
    plant_location, region, industry_type, consent_type, consent_status,
    valid_until, compliance_status, air_emission_category, water_discharge_category,
    hazardous_waste, environmental_clearance_required, simulate_outage
) VALUES
    ('MPCB-8821', 'PROJ-102', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'MIDC Pune', 'Pune', 'Chemical', 'CTE', 'APPROVED',
     '2027-03-31', 'COMPLIANT', 'RED', 'HIGH', TRUE, FALSE, FALSE),

    ('MPCB-8822', 'PROJ-103', 'ABC Industries Pvt Ltd', 'ABCDE1234F',
     'MIDC Pune', 'Pune', 'Chemical', 'CTO', 'PENDING',
     NULL, 'UNDER_REVIEW', 'RED', 'HIGH', TRUE, FALSE, FALSE),

    ('MPCB-8823', 'PROJ-104', 'XYZ Textiles Ltd', 'XYZPT5678K',
     'MIDC Nashik', 'Nashik', 'Textile', 'CTE', 'REJECTED',
     NULL, 'NON_COMPLIANT', 'ORANGE', 'MEDIUM', FALSE, FALSE, FALSE),

    ('MPCB-8824', 'PROJ-105', 'Konkan Ventures LLP', 'KONVL9012M',
     'MIDC Panvel', 'Raigad', 'Chemical', 'CTE', 'UNDER_OBJECTION',
     NULL, 'ACTION_REQUIRED', 'RED', 'HIGH', TRUE, TRUE, FALSE),

    ('MPCB-8999', 'PROJ-999', 'Demo Outage Corp', 'OUTAG0000Z',
     'MIDC Pune', 'Pune', 'Chemical', 'CTE', 'APPROVED',
     '2027-12-31', 'COMPLIANT', 'RED', 'HIGH', TRUE, FALSE, TRUE)
ON CONFLICT (application_no) DO NOTHING;
