const express = require('express');
const { requirePermission } = require('../middleware/auth');
const store = require('../data/store');
const { toCanonical, detectSchemaDrift } = require('../utils/schemaMapper');
const { evaluateLandDependency } = require('../utils/policyEngine');
const { auditMiddleware, getRecentTransactions } = require('../utils/audit');
const { shouldSimulateFailure, sendSimulatedOutage } = require('../utils/failureSimulator');
const { notifyGatewayOfMutationChange } = require('../utils/webhookNotifier');

const router = express.Router();

/**
 * ============================================================================
 * MAHARASHTRA BHUMI ABHILEKH (MAHABHULEKH / महाभूमी) OFFICIAL API ENDPOINTS
 * ============================================================================
 */

/**
 * GET /api/land/mahabhulekh/divisions
 * Returns Maharashtra administrative divisions (पुणे, कोकण, नाशिक, छत्रपती संभाजीनगर, अमरावती, नागपूर)
 */
router.get('/mahabhulekh/divisions', (req, res) => {
  const data = store.getDivisionsData();
  res.json({
    success: true,
    portal: 'MahaBhulekh (महाराष्ट्र भूमी अभिलेख)',
    authority: 'Revenue and Forest Department, Government of Maharashtra (महसूल व वन विभाग)',
    divisions: data.divisions
  });
});

/**
 * GET /api/land/mahabhulekh/7-12
 * Searches and returns official Form 7 & Form 12 (गाव नमुना ७ व १२ - सातबारा उतारा)
 * Query params: division, district, taluka, village, searchType (survey|khata|name|pan), query
 */
router.get('/mahabhulekh/7-12', async (req, res) => {
  const { division, district, taluka, village, searchType, query, surveyNumber, pan } = req.query;
  const targetQuery = query || surveyNumber || pan || '101';
  const targetSearchType = searchType || (surveyNumber ? 'survey' : (pan ? 'pan' : 'survey'));

  const results = await store.searchMahaBhulekh({
    division,
    district,
    taluka,
    village,
    searchType: targetSearchType,
    query: targetQuery
  });

  if (!results || results.length === 0) {
    return res.status(404).json({
      success: false,
      error: 'Not Found',
      message: `महाराष्ट्र भूमी अभिलेख प्रणालीमध्ये संबंधित रेकॉर्ड आढळले नाही (No 7/12 record found for "${targetQuery}").`
    });
  }

  const record = results[0];
  const { simulateOutage, ...cleanRecord } = record;

  res.json({
    success: true,
    portal: 'MahaBhulekh (महाभूमी)',
    form_type: 'गाव नमुना ७ व १२ (Village Form VII & XII - 7/12 Extract)',
    district: cleanRecord.district_mr || cleanRecord.district,
    taluka: cleanRecord.taluka_mr || cleanRecord.taluka,
    village: cleanRecord.village_mr || cleanRecord.village,
    uin: `MH-${(cleanRecord.district || 'PUN').substring(0, 3).toUpperCase()}-${cleanRecord.gtn}-${Date.now().toString(36).toUpperCase()}`,
    record: cleanRecord,
    total_matching: results.length,
    canonical: toCanonical(cleanRecord)
  });
});

/**
 * GET /api/land/mahabhulekh/8-a
 * Returns Form 8-A (गाव नमुना ८-अ - खाते उतारा / Holding Sheet)
 */
router.get('/mahabhulekh/8-a', async (req, res) => {
  const { khataNo, pan, name, query } = req.query;
  const target = khataNo || pan || name || query || '452';

  const extract = await store.get8AExtract(target);
  if (!extract) {
    return res.status(404).json({
      success: false,
      error: 'Not Found',
      message: `गाव नमुना ८-अ खाते उतारा आढळला नाही (No 8-A extract found for "${target}").`
    });
  }

  res.json({
    success: true,
    portal: 'MahaBhulekh (महाभूमी)',
    form_type: 'गाव नमुना ८-अ (Village Form VIII-A - Khate Utapa)',
    extract
  });
});

/**
 * GET /api/land/mahabhulekh/ferfar
 * Returns e-Ferfar mutation records (ई-फेरफार नोंद)
 */
router.get('/mahabhulekh/ferfar', async (req, res) => {
  const { ferfarNo, surveyNumber } = req.query;
  const list = await store.getFerfarRecords(ferfarNo || surveyNumber);

  res.json({
    success: true,
    portal: 'MahaBhulekh e-Ferfar (ई-महाभूमी)',
    count: list.length,
    ferfar_records: list
  });
});

/**
 * GET /api/land/mahabhulekh/aapli-chawadi
 * Returns Aapli Chawadi Section 135-D public notices (आपली चावडी डिजिटल फलक)
 */
router.get('/mahabhulekh/aapli-chawadi', async (req, res) => {
  const { village, taluka } = req.query;
  const notices = await store.getAapliChawadiNotices(village || taluka);

  res.json({
    success: true,
    portal: 'Aapli Chawadi (आपली चावडी - महसूल विभाग)',
    description: 'महाराष्ट्र जमीन महसूल संहिता १९६६ कलम १३५-ड अन्वये नोटीस फलक',
    count: notices.length,
    notices
  });
});

/**
 * ============================================================================
 * CORE & INTEROPERABILITY GATEWAY COMPATIBILITY ENDPOINTS
 * ============================================================================
 */

/**
 * GET /api/land/all
 * Returns all land records.
 */
router.get('/all', async (req, res) => {
  const all = await store.getAllRecords();
  res.json({ success: true, count: all.length, records: all });
});

/**
 * POST /api/land/apply
 * Submits a new land application / mutation.
 */
router.post('/apply', async (req, res) => {
  const { surveyNumber, pan, applicantName, district, taluka, village, area, certificateType } = req.body || {};
  if (!surveyNumber || !pan) {
    return res.status(400).json({ error: 'Bad Request', message: 'Both "surveyNumber" and "pan" are required.' });
  }

  const existing = await store.getRecord(surveyNumber);
  const status = existing ? existing.jamabandi : 'PENDING';

  const newRecord = {
    gtn: String(surveyNumber).trim(),
    survey_number: String(surveyNumber).trim(),
    malak_name: applicantName || (existing ? existing.malak_name : 'Applicant'),
    malak_pan: String(pan).trim().toUpperCase(),
    kshetra: area ? String(area) : (existing ? existing.kshetra : '5.0'),
    kshetra_unit: 'HA',
    jamabandi: status,
    jamin_prakar: 'INDUSTRIAL',
    bandhak: false,
    court_case: false,
    district: district || 'Pune',
    taluka: taluka || 'Haveli',
    village: village || 'Wagholi'
  };

  const saved = await store.saveRecord(newRecord);
  res.json({
    success: true,
    message: 'Land certificate application recorded successfully.',
    application_ref: `LND-MH-${saved.gtn}-${saved.jamabandi}`,
    record: saved
  });
});

/**
 * GET /api/land/records/:surveyNumber
 * Returns the raw, legacy-shaped record — by GTN or PAN.
 */
router.get(
  '/records/:surveyNumber',
  requirePermission('read:records'),
  auditMiddleware('GET /records/:surveyNumber', (req) => req.params.surveyNumber),
  async (req, res) => {
    const record = await store.getRecord(req.params.surveyNumber);

    if (shouldSimulateFailure(req, record)) return sendSimulatedOutage(res);

    if (!record) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No land record found for survey number or PAN "${req.params.surveyNumber}".`
      });
    }

    const { simulateOutage, ...cleanRecord } = record;
    const payload = req.query.schema === 'canonical' ? toCanonical(cleanRecord) : cleanRecord;
    res.json(payload);
  }
);

/**
 * GET /api/land/status/:surveyNumber
 * Lightweight mutation-status check, in canonical field names
 */
router.get(
  '/status/:surveyNumber',
  requirePermission('read:status'),
  auditMiddleware('GET /status/:surveyNumber', (req) => req.params.surveyNumber),
  async (req, res) => {
    const record = await store.getRecord(req.params.surveyNumber);

    if (shouldSimulateFailure(req, record)) return sendSimulatedOutage(res);

    if (!record) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No land record found for survey number ${req.params.surveyNumber}.`
      });
    }

    const { simulateOutage, ...cleanRecord } = record;
    const canonical = toCanonical(cleanRecord);
    res.json({
      survey_number: canonical.survey_number,
      mutation_status: canonical.mutation_status,
      encumbrance_free: canonical.encumbrance_free,
      dispute_free: canonical.dispute_free,
      last_updated: new Date().toISOString(),
      retryable: canonical.mutation_status === 'PENDING'
    });
  }
);

/**
 * POST /api/land/verify
 * Body: { surveyNumber, pan }
 */
router.post(
  '/verify',
  requirePermission('verify'),
  auditMiddleware('POST /verify', (req) => req.body && req.body.surveyNumber),
  async (req, res) => {
    const { surveyNumber, pan, applicantName, district, taluka, village, area } = req.body || {};

    if (!surveyNumber || !pan) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Both "surveyNumber" and "pan" are required in the request body.'
      });
    }

    let record = await store.getRecord(surveyNumber);

    if (shouldSimulateFailure(req, record)) return sendSimulatedOutage(res);

    // If record doesn't exist yet, register it dynamically for this applicant!
    if (!record) {
      record = await store.saveRecord({
        gtn: String(surveyNumber).trim(),
        survey_number: String(surveyNumber).trim(),
        malak_name: applicantName || 'Registered Applicant',
        malak_pan: String(pan).trim().toUpperCase(),
        kshetra: area ? String(area) : '5.0',
        kshetra_unit: 'HA',
        jamabandi: 'APPROVED',
        jamin_prakar: 'INDUSTRIAL',
        bandhak: false,
        court_case: false,
        district: district || 'Pune',
        taluka: taluka || 'Haveli',
        village: village || 'Wagholi'
      });
    }

    // (Reference zip auto-approved PENDING records 10 s after a verify call and
    // fired the webhook. Left out: it silently changes department state.)

    const { simulateOutage, ...cleanRecord } = record;
    const canonical = toCanonical(cleanRecord);
    const { checks, dependency_status } = evaluateLandDependency(canonical, pan);

    res.json({
      survey_number: canonical.survey_number,
      canonical,
      checks,
      dependency_status
    });
  }
);

/**
 * PATCH /api/land/records/:surveyNumber/mutation
 */
router.patch(
  '/records/:surveyNumber/mutation',
  requirePermission('admin:mutation'),
  auditMiddleware('PATCH /records/:surveyNumber/mutation', (req) => req.params.surveyNumber),
  async (req, res) => {
    const { mutation_status } = req.body || {};

    if (!mutation_status || !store.VALID_MUTATION_STATUSES.includes(mutation_status)) {
      return res.status(400).json({
        error: 'Bad Request',
        message: `"mutation_status" must be one of: ${store.VALID_MUTATION_STATUSES.join(', ')}.`
      });
    }

    const updated = await store.updateMutationStatus(req.params.surveyNumber, mutation_status);

    if (!updated) {
      return res.status(404).json({
        error: 'Not Found',
        message: `No land record found for survey number ${req.params.surveyNumber}.`
      });
    }

    notifyGatewayOfMutationChange(updated);

    res.json({
      survey_number: updated.gtn,
      mutation_status: updated.jamabandi,
      note: 'Persisted to live store. Gateway notified.'
    });
  }
);

/**
 * POST /api/land/schema-mapping/detect
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
 * GET /api/land/audit
 */
router.get('/audit', requirePermission('read:audit'), (req, res) => {
  const limit = Math.min(parseInt(req.query.limit, 10) || 50, 500);
  res.json({ transactions: getRecentTransactions(limit) });
});

module.exports = router;
