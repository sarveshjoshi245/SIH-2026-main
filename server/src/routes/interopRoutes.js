import express from 'express';
import fs from 'fs';
import { db } from '../db/seedData.js';

const router = express.Router();

// ─── API Configuration ────────────────────────────────────────────────────────
// Department addresses come from the repo-root ports.json (single source of truth).
const PORTS = JSON.parse(fs.readFileSync(new URL('../../../ports.json', import.meta.url), 'utf8'));
const deptUrl = (name) => `http://${PORTS.host}:${PORTS.services[name].port}`;
const LAND_API_URL      = deptUrl('land');
const ELEC_API_URL      = deptUrl('electricity');
const POLLUTION_API_URL = deptUrl('pollution');
const INTEROP_API_KEY  = 'interop-demo-key-001';
const ELEC_API_KEY     = 'elec_live_interop_key_991';

// ─── Helper: Canonicalizer for Citizen Land Records ──────────────────────────
export function normalizeLandSchema(rawLandData) {
  if (!rawLandData) return null;

  const surveyNumber = rawLandData.gtn || rawLandData.survey_no || rawLandData.surveyNumber;
  const ownerName    = rawLandData.malak_name || rawLandData.owner_name || rawLandData.owner;
  const ownerPan     = rawLandData.malak_pan  || rawLandData.pan        || rawLandData.ownerPAN;
  const ownerAadhaar = rawLandData.malak_aadhaar || rawLandData.aadhaar;
  const areaHectares = parseFloat(rawLandData.kshetra || rawLandData.area || 0);
  const mutationStatus = rawLandData.jamabandi || rawLandData.mutation_status || rawLandData.mutationStatus;
  const landCategory = rawLandData.jamin_prakar || rawLandData.land_type || rawLandData.landCategory;
  const isEncumbered = rawLandData.bandhak !== undefined ? Boolean(rawLandData.bandhak) : Boolean(rawLandData.encumbered);
  const hasCourtCase = rawLandData.court_case !== undefined ? Boolean(rawLandData.court_case) : Boolean(rawLandData.hasCourtDispute);

  return {
    survey_number:      String(surveyNumber),
    citizen_name:       ownerName,
    citizen_pan:        ownerPan,
    citizen_aadhaar:    ownerAadhaar,
    area_hectares:      areaHectares,
    area_unit:          'HA',
    mutation_status:    mutationStatus, // APPROVED | PENDING | UNDER_OBJECTION
    land_category:      landCategory,  // AGRICULTURAL | RESIDENTIAL | COMMERCIAL | INDUSTRIAL
    encumbrance_status: isEncumbered ? 'ENCUMBERED' : 'CLEAR',
    has_court_case:     hasCourtCase,
    district:           rawLandData.district || rawLandData.jilha || 'Pune',
    taluka:             rawLandData.taluka   || 'Haveli',
    village:            rawLandData.village  || rawLandData.gaw   || 'N/A',
    normalized_at:      new Date().toISOString()
  };
}

// ─── POST /api/interop/evaluate-project ──────────────────────────────────────
// G2C Citizen Prerequisites Evaluation Engine
// Proxies to the real Land API at port 4000 for live data.
// Falls back to in-memory db if the Land API is unreachable.
router.post('/evaluate-project', async (req, res) => {
  const { applicantPan, applicantAadhaar, surveyNumber } = req.body;

  if (!surveyNumber) {
    return res.status(400).json({ success: false, message: 'Survey Number required for evaluation' });
  }

  let rawLand = null;
  let sourcedFrom = 'land-api';

  // Try real Land API first
  try {
    const landRes = await fetch(`${LAND_API_URL}/api/land/records/${surveyNumber}`, {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': INTEROP_API_KEY
      },
      signal: AbortSignal.timeout(5000)
    });

    if (landRes.ok) {
      rawLand = await landRes.json();
    } else if (landRes.status === 404) {
      return res.status(404).json({
        success: false,
        message: `Land Record for Survey #${surveyNumber} not found in Land Department database`
      });
    } else if (landRes.status === 503) {
      // Circuit-breaker: fall through to in-memory fallback
      sourcedFrom = 'fallback';
    }
  } catch (fetchErr) {
    console.warn('[Interop] Land API unreachable, using fallback:', fetchErr.message);
    sourcedFrom = 'fallback';
  }

  // Fallback to in-memory seed data
  if (!rawLand) {
    rawLand = db.landRecords[surveyNumber];
  }

  if (!rawLand) {
    return res.status(404).json({
      success: false,
      message: `Land Record for Survey #${surveyNumber} could not be retrieved`
    });
  }

  // 1. Canonical transformation
  const canonicalLand = normalizeLandSchema(rawLand);

  // 2. Policy Engine — PAN / Aadhaar identity check
  const panMatch = applicantPan
    ? (canonicalLand.citizen_pan === applicantPan.toUpperCase())
    : true;
  const aadhaarMatch = applicantAadhaar
    ? (canonicalLand.citizen_aadhaar === applicantAadhaar.replace(/[\s-]/g, ''))
    : true;
  const identityMatch = panMatch && aadhaarMatch;

  const mutationApproved    = canonicalLand.mutation_status === 'APPROVED';
  const isClearEncumbrance  = canonicalLand.encumbrance_status === 'CLEAR';
  const noLegalDispute      = !canonicalLand.has_court_case;

  const landDependencyResolved = identityMatch && mutationApproved && isClearEncumbrance && noLegalDispute;

  let dependencyStatus = 'RESOLVED';
  let pendingReason    = null;

  if (!identityMatch) {
    dependencyStatus = 'FAILED';
    pendingReason = `Identity mismatch: supplied PAN does not match Land Ownership Record (owner PAN: ${canonicalLand.citizen_pan}).`;
  } else if (canonicalLand.mutation_status === 'PENDING') {
    dependencyStatus = 'WAITING';
    pendingReason = 'Land Mutation (7/12 Jamabandi) is PENDING at Tahsildar / Revenue Department.';
  } else if (canonicalLand.mutation_status === 'UNDER_OBJECTION') {
    dependencyStatus = 'ACTION_REQUIRED';
    pendingReason = 'Land Record is UNDER OBJECTION due to pending mutation query at Sub-Registrar.';
  } else if (!isClearEncumbrance) {
    dependencyStatus = 'ACTION_REQUIRED';
    pendingReason = 'Active bank encumbrance flag present on land record (Bandhak = true). NOC required.';
  } else if (canonicalLand.has_court_case) {
    dependencyStatus = 'BLOCKED';
    pendingReason = 'Land record has an active civil court dispute flag.';
  }

  // 3. G2C Citizen Workflow Dependency Tree
  const workflowState = {
    applicationId:   `G2C-MH-2026-${surveyNumber}`,
    surveyNumber,
    lastEvaluatedAt: new Date().toISOString(),
    sourcedFrom,
    overallStatus:   landDependencyResolved ? 'READY_FOR_CITIZEN_SCHEME' : 'DEPENDENCY_WAITING',
    dependencies: [
      {
        id:          'DEP-LAND-01',
        title:       'Land Ownership & 7/12 Jamabandi Verification',
        department:  'Land Revenue & Settlement Department',
        status:      dependencyStatus,
        reason:      pendingReason,
        lastChecked: new Date().toISOString(),
        details:     canonicalLand
      },
      {
        id:         'DEP-AGRI-02',
        title:      'DBT Farmer Subsidy / Agricultural Approval',
        department: 'Department of Agriculture, Govt. of Maharashtra',
        status:     landDependencyResolved ? 'IN_PROGRESS' : 'WAITING_FOR_PREREQUISITE',
        reason:     landDependencyResolved
          ? 'Land Verification satisfied. Application sent for sanction.'
          : 'Blocked: Waiting for Land Verification = RESOLVED',
        lastChecked: new Date().toISOString()
      },
      {
        id:         'DEP-ELEC-03',
        title:      'Agri-Pump Electricity Meter Connection',
        department: 'MSEDCL / Mahavitaran',
        status:     landDependencyResolved ? 'IN_PROGRESS' : 'WAITING_FOR_PREREQUISITE',
        reason:     landDependencyResolved
          ? 'Prerequisite Land Ownership verified.'
          : 'Blocked: Waiting for Land Verification = RESOLVED',
        lastChecked: new Date().toISOString()
      }
    ]
  };

  db.auditLogs.push({
    id:          `AUD-G2C-${Date.now()}`,
    timestamp:   new Date().toISOString(),
    event:       'CITIZEN_DEPENDENCY_EVALUATED',
    surveyNumber,
    status:      dependencyStatus
  });

  res.json({
    success:          true,
    workflow:         workflowState,
    rawLegacyPayload: rawLand,
    canonicalModel:   canonicalLand
  });
});

// ─── POST /api/interop/verify-electricity ────────────────────────────────────
// Proxy to the real Electricity Department API at port 8001 (from ports.json)
router.post('/verify-electricity', async (req, res) => {
  const { applicationNumber, pan } = req.body;

  if (!applicationNumber || !pan) {
    return res.status(400).json({
      success: false,
      message: 'applicationNumber and pan are required'
    });
  }

  try {
    const elecRes = await fetch(`${ELEC_API_URL}/api/electricity/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': ELEC_API_KEY
      },
      body: JSON.stringify({ application_number: applicationNumber, pan: pan.toUpperCase() }),
      signal: AbortSignal.timeout(8000)
    });

    const data = await elecRes.json();

    if (!elecRes.ok) {
      return res.status(elecRes.status).json({
        success: false,
        message: data.message || data.detail || 'Electricity API returned an error',
        raw: data
      });
    }

    // data.pan_match: true/false, data.application: legacy fields
    const app = data.application || {};
    const dependencyStatus = (data.pan_match && app.appl_stat === 'APPROVED') ? 'RESOLVED'
                           : (!data.pan_match)                                 ? 'FAILED'
                           : (app.appl_stat === 'PENDING' || app.appl_stat === 'UNDER_SCRUTINY') ? 'WAITING'
                           : (app.appl_stat === 'REJECTED')                    ? 'BLOCKED'
                           : 'IN_PROGRESS';

    db.auditLogs.push({
      id:              `AUD-ELEC-${Date.now()}`,
      timestamp:       new Date().toISOString(),
      event:           'ELECTRICITY_VERIFICATION',
      applicationNumber,
      status:          dependencyStatus,
      pan_match:       data.pan_match
    });

    res.json({
      success:          true,
      department:       'MSEDCL Electricity Distribution',
      dependency_status: dependencyStatus,
      pan_match:        data.pan_match,
      transaction_id:   data.transaction_id,
      application: {
        appl_no:    app.appl_no,
        appl_stat:  app.appl_stat,
        load_sanc:  app.load_sanc,
        meter_stat: app.meter_stat,
        conn_stat:  app.conn_stat,
        dues_flag:  app.dues_flag,
        cust_pan:   app.cust_pan
      }
    });
  } catch (err) {
    console.error('[Interop] Electricity API error:', err.message);
    res.status(503).json({
      success: false,
      message: 'Electricity Department API is currently unavailable (Circuit Open). Please retry.',
      retryable: true
    });
  }
});

// ─── POST /api/interop/verify-pollution ──────────────────────────────────────
// Proxy to the real Pollution Department API at port 4002
router.post('/verify-pollution', async (req, res) => {
  const { applicationNo, pan, industryType } = req.body;

  if (!applicationNo || !pan) {
    return res.status(400).json({
      success: false,
      message: 'applicationNo and pan are required'
    });
  }

  try {
    const pollRes = await fetch(`${POLLUTION_API_URL}/api/pollution/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': INTEROP_API_KEY
      },
      body: JSON.stringify({
        applicationNo,
        pan: pan.toUpperCase(),
        industryType: industryType || 'Manufacturing'
      }),
      signal: AbortSignal.timeout(8000)
    });

    const data = await pollRes.json();

    if (!pollRes.ok) {
      return res.status(pollRes.status).json({
        success: false,
        message: data.message || data.error || 'Pollution API returned an error',
        raw: data
      });
    }

    const depStatus = data.dependency_status || 'UNKNOWN';

    db.auditLogs.push({
      id:             `AUD-POLL-${Date.now()}`,
      timestamp:      new Date().toISOString(),
      event:          'POLLUTION_VERIFICATION',
      applicationNo,
      status:         depStatus
    });

    res.json({
      success:           true,
      department:        'Maharashtra Pollution Control Board (MPCB)',
      dependency_status: depStatus,
      application_no:    data.application_no,
      project_id:        data.project_id,
      canonical:         data.canonical,
      checks:            data.checks
    });
  } catch (err) {
    console.error('[Interop] Pollution API error:', err.message);
    res.status(503).json({
      success: false,
      message: 'Pollution Control Board API is currently unavailable (Circuit Open). Please retry.',
      retryable: true
    });
  }
});

// ─── GET /api/interop/audit-logs ─────────────────────────────────────────────
router.get('/audit-logs', (req, res) => {
  res.json({
    success:   true,
    totalLogs: db.auditLogs.length,
    logs:      db.auditLogs.slice().reverse()
  });
});

export default router;
