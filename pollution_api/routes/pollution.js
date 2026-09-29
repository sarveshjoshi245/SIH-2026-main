const express = require('express');
const { requirePermission } = require('../middleware/auth');
const store = require('../data/store');
const { toCanonical, detectSchemaDrift } = require('../utils/schemaMapper');
const { evaluatePollutionDependency } = require('../utils/policyEngine');
const { auditMiddleware, getRecentTransactions } = require('../utils/audit');
const { shouldSimulateFailure, sendSimulatedOutage } = require('../utils/failureSimulator');

const router = express.Router();

/**
 * GET /api/pollution/all
 * Returns all pollution applications from PostgreSQL.
 */
router.get('/all', async (req, res) => {
  const all = await store.getAllApplications();
  res.json({ success: true, count: all.length, applications: all });
});

/**
 * POST /api/pollution/apply
 * Submits a new MPCB consent application and persists it to PostgreSQL.
 */
router.post('/apply', async (req, res) => {
  const { applicationNo, industryName, industryPan, plantLocation, region, industryType, consentType, airEmissionCategory } = req.body || {};
  const appNo = applicationNo || `MPCB-${Date.now().toString().slice(-4)}`;

  const saved = await store.saveApplication({
    application_no: appNo,
    application_project_id: `PROJ-${appNo}`,
    industry_name: industryName || 'Enterprise Applicant',
    industry_pan: String(industryPan || '').trim().toUpperCase(),
    plant_location: plantLocation || 'MIDC Industrial Area',
    region: region || 'Pune',
    industry_type: industryType || 'Manufacturing',
    consent_type: consentType || 'CTE',
    consent_status: 'APPROVED',
    compliance_status: 'COMPLIANT',
    air_emission_category: airEmissionCategory || 'RED',
    water_discharge_category: 'MEDIUM',
    hazardous_waste: false,
    environmental_clearance_required: false
  });

  res.json({
    success: true,
    message: 'MPCB Consent application recorded successfully.',
    application_no: saved.application_no,
    consent_status: saved.consent_status,
    application: saved
  });
});

/**
 * GET /api/pollution/applications/:applicationNo
 * Returns the Pollution Department's native schema from PostgreSQL.
 */
router.get(
  '/applications/:applicationNo',
  requirePermission('read:applications'),
  auditMiddleware('GET /applications/:applicationNo', (req) => req.params.applicationNo),
  async (req, res) => {
    const application = await store.getApplication(req.params.applicationNo);

    if (shouldSimulateFailure(req, application)) return sendSimulatedOutage(res);

    if (!application) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No pollution application found for application number or PAN "${req.params.applicationNo}".`
      });
    }

    const { simulateOutage, ...cleanApplication } = application;
    const payload = req.query.schema === 'canonical'
      ? toCanonical(cleanApplication)
      : cleanApplication;

    res.json(payload);
  }
);

/**
 * GET /api/pollution/status/:applicationNo
 */
router.get(
  '/status/:applicationNo',
  requirePermission('read:status'),
  auditMiddleware('GET /status/:applicationNo', (req) => req.params.applicationNo),
  async (req, res) => {
    const application = await store.getApplication(req.params.applicationNo);

    if (shouldSimulateFailure(req, application)) return sendSimulatedOutage(res);

    if (!application) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No pollution application found for application number ${req.params.applicationNo}.`
      });
    }

    res.json({
      application_no: application.application_no,
      project_id: application.application_project_id,
      consent_status: application.consent_status,
      valid_until: application.valid_until,
      compliance_status: application.compliance_status
    });
  }
);

/**
 * POST /api/pollution/verify
 * Body: { applicationNo, pan, industryType }
 * Runs deterministic consent/compliance checks and returns canonical facts.
 */
router.post(
  '/verify',
  requirePermission('verify'),
  auditMiddleware('POST /verify', (req) => req.body && req.body.applicationNo),
  (req, res) => {
    const { applicationNo, pan, industryType } = req.body || {};

    if (!applicationNo || !pan) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Both "applicationNo" and "pan" are required. "industryType" is optional but recommended for full verification.'
      });
    }

    const application = store.getApplication(applicationNo);

    if (shouldSimulateFailure(req, application)) return sendSimulatedOutage(res);

    if (!application) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No pollution application found for application number ${applicationNo}.`
      });
    }

    const { simulateOutage, ...cleanApplication } = application;
    const canonical = toCanonical(cleanApplication);
    const { checks, dependency_status } = evaluatePollutionDependency(
      canonical,
      pan,
      industryType || canonical.industry_type
    );

    res.json({
      application_no: canonical.environment_application_number,
      project_id: canonical.project_id,
      canonical,
      checks,
      dependency_status
    });
  }
);

/**
 * PATCH /api/pollution/applications/:applicationNo/consent
 * Demo-only department action. Allows the simulated department to advance
 * consent status and demonstrate WAITING -> RESOLVED/ACTION_REQUIRED.
 */
router.patch(
  '/applications/:applicationNo/consent',
  requirePermission('admin:consent'),
  auditMiddleware('PATCH /applications/:applicationNo/consent', (req) => req.params.applicationNo),
  (req, res) => {
    const { consent_status } = req.body || {};

    if (!consent_status || !store.VALID_CONSENT_STATUSES.includes(consent_status)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `"consent_status" must be one of: ${store.VALID_CONSENT_STATUSES.join(', ')}.`
      });
    }

    const updated = store.updateConsentStatus(req.params.applicationNo, consent_status);

    if (!updated) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No pollution application found for application number ${req.params.applicationNo}.`
      });
    }

    res.json({
      application_no: updated.application_no,
      consent_status: updated.consent_status,
      valid_until: updated.valid_until,
      compliance_status: updated.compliance_status,
      note: 'In-memory demo update only — resets on server restart.'
    });
  }
);

/**
 * POST /api/pollution/schema-mapping/detect
 * Suggests mappings for fields introduced by a drifted Pollution schema.
 */
router.post(
  '/schema-mapping/detect',
  requirePermission('detect:schema-drift'),
  auditMiddleware('POST /schema-mapping/detect', () => null),
  (req, res) => {
    const payload = req.body || {};

    if (Object.keys(payload).length === 0) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Provide a JSON body representing the record to check for schema drift.'
      });
    }

    res.json(detectSchemaDrift(payload));
  }
);

/**
 * GET /api/pollution/audit
 * Recent departmental transaction log.
 */
router.get('/audit', requirePermission('read:audit'), (req, res) => {
  const limit = Math.min(parseInt(req.query.limit, 10) || 50, 500);
  res.json({ transactions: getRecentTransactions(limit) });
});

module.exports = router;
