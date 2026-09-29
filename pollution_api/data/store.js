const { Pool } = require('pg');
const seedApplications = require('./pollutionApplications.json');

/**
 * PostgreSQL-backed store with automatic JSON fallback.
 * Loads records directly from the 'pollution_department' database on startup.
 */
const applications = new Map(
  seedApplications.map((application) => [application.application_no, { ...application }])
);

const VALID_CONSENT_STATUSES = [
  'PENDING',
  'APPROVED',
  'REJECTED',
  'UNDER_OBJECTION'
];

const VALID_COMPLIANCE_STATUSES = [
  'COMPLIANT',
  'UNDER_REVIEW',
  'ACTION_REQUIRED',
  'NON_COMPLIANT'
];

const pgConnectionString = process.env.DATABASE_URL || 'postgresql://postgres:Ajinkya%401115@localhost:5432/pollution_department';
let pool = null;

try {
  pool = new Pool({ connectionString: pgConnectionString });
  pool.query('SELECT * FROM pollution_applications', (err, res) => {
    if (!err && res && res.rows) {
      res.rows.forEach((r) => {
        applications.set(String(r.application_no), {
          application_no: String(r.application_no),
          application_project_id: r.application_project_id,
          industry_name: r.industry_name,
          industry_pan: r.industry_pan,
          plant_location: r.plant_location,
          region: r.region,
          industry_type: r.industry_type,
          consent_type: r.consent_type,
          consent_status: r.consent_status,
          valid_until: r.valid_until ? r.valid_until.toISOString().split('T')[0] : null,
          compliance_status: r.compliance_status,
          air_emission_category: r.air_emission_category,
          water_discharge_category: r.water_discharge_category,
          hazardous_waste: Boolean(r.hazardous_waste),
          environmental_clearance_required: Boolean(r.environmental_clearance_required),
          simulateOutage: Boolean(r.simulate_outage)
        });
      });
      console.log(`[Pollution API] Connected to PostgreSQL (pollution_department) — ${res.rows.length} applications loaded.`);
    } else if (err) {
      console.warn('[Pollution API] PostgreSQL query error, using local fallback:', err.message);
    }
  });
} catch (e) {
  console.warn('[Pollution API] PostgreSQL connection error, using local fallback:', e.message);
}

async function getApplication(applicationNoOrPan) {
  const query = String(applicationNoOrPan).trim();
  if (pool) {
    try {
      const res = await pool.query(
        'SELECT * FROM pollution_applications WHERE application_no = $1 OR UPPER(industry_pan) = UPPER($1) LIMIT 1',
        [query]
      );
      if (res.rows && res.rows.length > 0) {
        const r = res.rows[0];
        const app = {
          application_no: String(r.application_no),
          application_project_id: r.application_project_id,
          industry_name: r.industry_name,
          industry_pan: r.industry_pan,
          plant_location: r.plant_location,
          region: r.region,
          industry_type: r.industry_type,
          consent_type: r.consent_type,
          consent_status: r.consent_status,
          valid_until: r.valid_until ? (r.valid_until.toISOString ? r.valid_until.toISOString().split('T')[0] : String(r.valid_until)) : null,
          compliance_status: r.compliance_status,
          air_emission_category: r.air_emission_category,
          water_discharge_category: r.water_discharge_category,
          hazardous_waste: Boolean(r.hazardous_waste),
          environmental_clearance_required: Boolean(r.environmental_clearance_required),
          simulateOutage: Boolean(r.simulate_outage)
        };
        applications.set(app.application_no, app);
        return app;
      }
    } catch (e) {
      console.warn('[Pollution API] getApplication error:', e.message);
    }
  }
  return applications.get(query) || Array.from(applications.values()).find(a => a.industry_pan?.toUpperCase() === query.toUpperCase()) || null;
}

async function getAllApplications() {
  if (pool) {
    try {
      const res = await pool.query('SELECT * FROM pollution_applications ORDER BY id ASC');
      if (res.rows && res.rows.length > 0) {
        const list = res.rows.map(r => ({
          application_no: String(r.application_no),
          application_project_id: r.application_project_id,
          industry_name: r.industry_name,
          industry_pan: r.industry_pan,
          plant_location: r.plant_location,
          region: r.region,
          industry_type: r.industry_type,
          consent_type: r.consent_type,
          consent_status: r.consent_status,
          valid_until: r.valid_until ? (r.valid_until.toISOString ? r.valid_until.toISOString().split('T')[0] : String(r.valid_until)) : null,
          compliance_status: r.compliance_status,
          air_emission_category: r.air_emission_category,
          water_discharge_category: r.water_discharge_category,
          hazardous_waste: Boolean(r.hazardous_waste),
          environmental_clearance_required: Boolean(r.environmental_clearance_required),
          simulateOutage: Boolean(r.simulate_outage)
        }));
        list.forEach(item => applications.set(item.application_no, item));
        return list;
      }
    } catch (e) {
      console.warn('[Pollution API] getAllApplications error:', e.message);
    }
  }
  return Array.from(applications.values());
}

async function saveApplication(app) {
  const appNo = String(app.application_no);
  applications.set(appNo, app);

  if (pool) {
    try {
      await pool.query(
        `INSERT INTO pollution_applications (application_no, application_project_id, industry_name, industry_pan, plant_location, region, industry_type, consent_type, consent_status, compliance_status, air_emission_category, water_discharge_category, hazardous_waste, environmental_clearance_required)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
         ON CONFLICT (application_no) DO UPDATE SET
           industry_name = EXCLUDED.industry_name,
           industry_pan = EXCLUDED.industry_pan,
           consent_status = EXCLUDED.consent_status,
           compliance_status = EXCLUDED.compliance_status`,
        [
          appNo,
          app.application_project_id || `PROJ-${appNo}`,
          app.industry_name,
          app.industry_pan,
          app.plant_location || 'MIDC Industrial Area',
          app.region || 'Pune',
          app.industry_type || 'Manufacturing',
          app.consent_type || 'CTE',
          app.consent_status || 'APPROVED',
          app.compliance_status || 'COMPLIANT',
          app.air_emission_category || 'RED',
          app.water_discharge_category || 'MEDIUM',
          app.hazardous_waste ? 1 : 0,
          app.environmental_clearance_required ? 1 : 0
        ]
      );
    } catch (e) {
      console.warn('[Pollution API] DB saveApplication error:', e.message);
    }
  }
  return app;
}

async function updateConsentStatus(applicationNo, newStatus) {
  const application = await getApplication(applicationNo);
  if (!application) return null;

  application.consent_status = newStatus;

  if (newStatus === 'APPROVED') {
    application.compliance_status = 'COMPLIANT';
    if (!application.valid_until) application.valid_until = '2027-03-31';
  } else if (newStatus === 'REJECTED') {
    application.compliance_status = 'NON_COMPLIANT';
    application.valid_until = null;
  } else if (newStatus === 'UNDER_OBJECTION') {
    application.compliance_status = 'ACTION_REQUIRED';
    application.valid_until = null;
  } else if (newStatus === 'PENDING') {
    application.compliance_status = 'UNDER_REVIEW';
    application.valid_until = null;
  }

  applications.set(String(applicationNo), application);

  if (pool) {
    try {
      await pool.query(
        'UPDATE pollution_applications SET consent_status = $1, compliance_status = $2, valid_until = $3 WHERE application_no = $4',
        [application.consent_status, application.compliance_status, application.valid_until, String(applicationNo)]
      );
    } catch (err) {
      console.warn('[Pollution API] Failed to persist consent update to PostgreSQL:', err.message);
    }
  }

  return application;
}

function listApplicationNumbers() {
  return Array.from(applications.keys());
}

module.exports = {
  getApplication,
  getAllApplications,
  saveApplication,
  updateConsentStatus,
  listApplicationNumbers,
  VALID_CONSENT_STATUSES,
  VALID_COMPLIANCE_STATUSES
};
