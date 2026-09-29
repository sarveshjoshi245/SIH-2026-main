import express from 'express';
import { getApplicationDetails, getAllProjectApplications, createFeedback, poolInterop } from '../db/database.js';

const router = express.Router();

// GET /api/portal/user-profile?pan=ABCDE1234F  — fetch full citizen+user profile from PostgreSQL
router.get('/user-profile', async (req, res) => {
  const { pan } = req.query;
  if (!pan) return res.status(400).json({ success: false, message: 'PAN is required' });

  try {
    // 1. Look up enterprise user
    const userRes = await poolInterop.query(
      `SELECT id, email, organization_name, organization_pan, role, is_active FROM users WHERE UPPER(organization_pan) = UPPER($1) LIMIT 1`,
      [pan.trim()]
    );
    // 2. Look up citizen KYC
    const citizenRes = await poolInterop.query(
      `SELECT id, first_name, last_name, mobile, email, aadhaar, pan FROM citizens WHERE UPPER(pan) = UPPER($1) LIMIT 1`,
      [pan.trim()]
    );

    const user = userRes.rows[0] || null;
    const citizen = citizenRes.rows[0] || null;

    if (!user && !citizen) {
      return res.json({ success: false, found: false, message: 'No user found for this PAN in the database.' });
    }

    // Merge into single profile
    const profile = {
      pan: pan.trim().toUpperCase(),
      organization_name: user?.organization_name || '',
      organization_pan: user?.organization_pan || pan.trim().toUpperCase(),
      email: user?.email || citizen?.email || '',
      role: user?.role || 'APPLICANT',
      // Citizen fields
      first_name: citizen?.first_name || '',
      last_name: citizen?.last_name || '',
      full_name: citizen ? `${citizen.first_name} ${citizen.last_name}` : (user?.organization_name || ''),
      mobile: citizen?.mobile || '',
      aadhaar: citizen?.aadhaar || ''
    };

    res.json({ success: true, found: true, profile });
  } catch (err) {
    console.error('[user-profile] DB error:', err.message);
    res.status(500).json({ success: false, message: 'Database error fetching profile.' });
  }
});

// GET /api/portal/applications-list - Return live list of departmental projects from PostgreSQL
router.get('/applications-list', async (req, res) => {
  try {
    const list = await getAllProjectApplications();
    res.json({ success: true, applications: list });
  } catch (err) {
    res.status(500).json({ success: false, message: 'Failed to fetch application list' });
  }
});

// POST /api/portal/status-check - Check live status from PostgreSQL & Department databases
router.post('/status-check', async (req, res) => {
  const { appId } = req.body;
  if (!appId) {
    return res.status(400).json({ success: false, message: 'Application ID or Survey Number is required.' });
  }

  const cleanId = appId.trim();

  try {
    const app = await getApplicationDetails(cleanId);

    if (!app || !app.found) {
      return res.json({
        success: true,
        found: false,
        message: `No active record found for '${cleanId}'. Please check your Application Reference Number.`,
        demoIds: ['APP-MH-2026-101', 'APP-MH-2026-102', 'APP-MH-2026-103', 'ELEC-2026-00101', 'MPCB-8821']
      });
    }

    res.json({
      success: true,
      found: true,
      application: app
    });
  } catch (err) {
    res.status(500).json({ success: false, message: 'Error retrieving application details from database.' });
  }
});

// POST /api/portal/feedback - Submit feedback or grievance
router.post('/feedback', (req, res) => {
  const { name, email, category, rating, message } = req.body;

  if (!name || !email || !message) {
    return res.status(400).json({ success: false, message: 'Name, email, and message are required.' });
  }

  try {
    createFeedback({
      name: name.trim(),
      email: email.trim(),
      category: category || 'GENERAL',
      rating: parseInt(rating, 10) || 5,
      message: message.trim()
    });

    res.json({
      success: true,
      message: 'Thank you for your feedback! Your reference ticket has been logged successfully.'
    });
  } catch (err) {
    res.status(500).json({ success: false, message: 'Failed to record feedback.' });
  }
});

// POST /api/portal/process-wizard - Investor/Citizen Process Wizard (MAITRI Question-based microservices recommendation)
// POST /api/portal/process-wizard - Investor/Citizen Process Wizard (RAG 10-Question Regulatory Evaluation)
router.post('/process-wizard', (req, res) => {
  const body = req.body;

  // Extract from 10-question interview format or fallback to legacy fields
  const projectType = (body.project_type || body.projectType || 'MANUFACTURING').toUpperCase();
  const industryType = (body.industry_type || body.industryType || 'GENERAL').toUpperCase();
  const district = body.location_district || body.district || 'Pune';

  const isLandReq = body.land_required !== undefined ? (String(body.land_required) === 'true' || body.land_required === true) : true;
  const landOwned = body.land_owned || (body.landAcquired === 'yes' ? 'Yes' : (body.landAcquired === 'no' ? 'No' : 'Yes'));
  const landArea = parseFloat(body.land_area || 3.0);

  const isElecReq = body.electricity_required !== undefined ? (String(body.electricity_required) === 'true' || body.electricity_required === true) : true;
  const elecLoadKw = parseFloat(body.electricity_load || (body.powerRequired === 'high' ? 300 : 50));

  const hasEmissions = String(body.industrial_emissions) === 'true' || body.envCategory === 'red' || body.envCategory === 'orange';
  const hasHazWaste = String(body.hazardous_waste) === 'true' || body.envCategory === 'red';

  const recommendedServices = [];
  const prerequisites = [];
  const analysisBreakdown = [];

  // ── Analysis 1 & 2: Project & Industry Type ──
  let pollutionTier = 'GREEN';
  if (hasHazWaste || (projectType === 'MANUFACTURING' && (industryType === 'CHEMICAL' || industryType === 'PHARMACEUTICAL'))) {
    pollutionTier = 'RED';
  } else if (hasEmissions || (projectType === 'MANUFACTURING' && (industryType === 'FOOD_PROCESSING' || industryType === 'TEXTILE'))) {
    pollutionTier = 'ORANGE';
  } else if (projectType === 'WAREHOUSE' || projectType === 'IT_OFFICE') {
    pollutionTier = 'WHITE_GREEN';
  }

  analysisBreakdown.push({
    questionNumber: 1,
    field: 'project_type',
    title: 'Project Nature & Sector',
    userSelection: projectType,
    implication: `Classified as ${projectType} under Maharashtra Industrial Policy. Determines core departmental jurisdiction.`
  });

  if (projectType === 'MANUFACTURING') {
    analysisBreakdown.push({
      questionNumber: 2,
      field: 'industry_type',
      title: 'Manufacturing Industry Classification',
      userSelection: industryType,
      implication: `${industryType} industry requires specific industrial safety inspection and pollution mitigation controls.`
    });
  }

  analysisBreakdown.push({
    questionNumber: 3,
    field: 'location_district',
    title: 'Jurisdiction & Location',
    userSelection: district,
    implication: `Governed by District Collectorate and Regional Office (${district} Circle).`
  });

  // ── Analysis 4, 5, 6: Land & Site ──
  if (isLandReq) {
    if (landOwned === 'Yes') {
      recommendedServices.push({
        departmentCode: 'LAND',
        code: 'LAND-VERIFY',
        title: '7/12 Land Mutation & Title Deed Verification',
        department: 'Revenue & Land Settlement Department',
        authority: `Collectorate & Tahsildar (${district})`,
        turnaroundDays: 7,
        priority: 'PREREQUISITE_STAGE_1',
        wave: 1,
        details: `Verification of 7/12 extract for approx ${landArea} Hectare(s). Mutation entry and non-encumbrance certificate required.`
      });
      prerequisites.push(`Survey / Gat Number in ${district} with valid 7/12 extract`);
      analysisBreakdown.push({
        questionNumber: 4,
        field: 'land',
        title: 'Land Prerequisite (Wave 1 Gate)',
        userSelection: `Owned Private Land (${landArea} Ha)`,
        implication: 'Must be verified as RESOLVED before any downstream electricity or pollution sanctions can be processed.'
      });
    } else {
      recommendedServices.push({
        departmentCode: 'LAND',
        code: 'MIDC-ALLOT',
        title: 'MIDC Industrial Plot Allotment & Lease Deed',
        department: 'Maharashtra Industrial Development Corporation (MIDC)',
        authority: `MIDC Regional Office (${district})`,
        turnaroundDays: 21,
        priority: 'PREREQUISITE_STAGE_1',
        wave: 1,
        details: `Industrial plot allotment for approx ${landArea} Hectare(s) in notified MIDC industrial area.`
      });
      prerequisites.push('Detailed Project Report (DPR) and financial net worth certification for MIDC allotment');
      analysisBreakdown.push({
        questionNumber: 4,
        field: 'land',
        title: 'Land Acquisition (Wave 1 Gate)',
        userSelection: `MIDC Allotment Required (${landArea} Ha)`,
        implication: 'MIDC provisional allotment letter acts as root land title for parallel clearances.'
      });
    }
  } else {
    analysisBreakdown.push({
      questionNumber: 4,
      field: 'land',
      title: 'Land Requirement',
      userSelection: 'No Physical Land Required',
      implication: 'Virtual or rented premises. Land mutation verification bypassed.'
    });
  }

  // ── Analysis 7 & 8: Electricity Load ──
  if (isElecReq) {
    const isHt = elecLoadKw >= 100;
    recommendedServices.push({
      departmentCode: 'ELECTRICITY',
      code: isHt ? 'MSEDCL-HT' : 'MSEDCL-LT',
      title: isHt ? `High Tension (HT) Power Feasibility (${elecLoadKw} kW)` : `Low Tension (LT) Commercial Supply (${elecLoadKw} kW)`,
      department: 'Maharashtra State Electricity Distribution Co. Ltd. (MSEDCL)',
      authority: isHt ? 'MSEDCL Chief Engineer / Circle Office' : 'MSEDCL Local Sub-Division',
      turnaroundDays: isHt ? 10 : 4,
      priority: 'STAGE_2_PARALLEL',
      wave: 2,
      loadKw: elecLoadKw,
      details: isHt ? `HT 11kV/22kV dedicated feeder connection. Transformer bay earmarking required.` : `LT 415V three-phase commercial connection.`
    });
    prerequisites.push(isHt ? 'Land title approval & transformer installation layout earmarked' : 'Premises ownership proof');
    analysisBreakdown.push({
      questionNumber: 7,
      field: 'electricity',
      title: 'Power Grid Sanction Demand',
      userSelection: `${elecLoadKw} kW (${isHt ? 'High Tension' : 'Low Tension'})`,
      implication: isHt ? 'Requires dedicated transformer site and technical grid feasibility report from MSEDCL.' : 'Standard LT service connection meter.'
    });
  }

  // ── Analysis 9 & 10: Environmental Emissions & Hazardous Waste ──
  if (pollutionTier === 'RED' || pollutionTier === 'ORANGE') {
    recommendedServices.push({
      departmentCode: 'POLLUTION',
      code: `MPCB-CTE-${pollutionTier}`,
      title: `Consent to Establish (CTE) — ${pollutionTier} Category`,
      department: 'Maharashtra Pollution Control Board (MPCB)',
      authority: `MPCB Regional Officer (${district})`,
      turnaroundDays: pollutionTier === 'RED' ? 21 : 14,
      priority: 'STAGE_2_PARALLEL',
      wave: 2,
      tier: pollutionTier,
      details: `${pollutionTier} category CTE under Water Act (1974) and Air Act (1981). ${hasHazWaste ? 'Hazardous waste authorization under HWMR rules required.' : 'Effluent Treatment Plant (ETP) plan mandatory.'}`
    });
    prerequisites.push('Verified land document / MIDC allotment + Detailed Environmental Management Plan (EMP)');
    analysisBreakdown.push({
      questionNumber: 9,
      field: 'environment',
      title: 'Environmental Consent Tier',
      userSelection: `${pollutionTier} Category (Emissions: ${hasEmissions ? 'Yes' : 'No'}, HazWaste: ${hasHazWaste ? 'Yes' : 'No'})`,
      implication: `Mandatory CTE clearance prior to any site construction. Auto-inherits verified land identity.`
    });
  } else {
    recommendedServices.push({
      departmentCode: 'POLLUTION',
      code: 'MPCB-GREEN',
      title: 'Green Category Intimation & White Exemption',
      department: 'Maharashtra Pollution Control Board (MPCB)',
      authority: 'MPCB Sub-Regional Office',
      turnaroundDays: 3,
      priority: 'STAGE_2_PARALLEL',
      wave: 2,
      tier: 'GREEN',
      details: 'Fast-track self-certification and pollution intimation for non-polluting activities.'
    });
    analysisBreakdown.push({
      questionNumber: 9,
      field: 'environment',
      title: 'Environmental Profile',
      userSelection: 'Low/Zero Emissions (Green Tier)',
      implication: 'Eligible for fast-track deemed clearance and immediate online intimation.'
    });
  }

  // DISH / Labour approval
  recommendedServices.push({
    departmentCode: 'DISH',
    code: 'FACTORY-ACT',
    title: 'Directorate of Industrial Safety & Health (DISH) Plan Approval',
    department: 'Labour & DISH Department',
    authority: 'Director of Industrial Safety',
    turnaroundDays: 12,
    priority: 'STAGE_3',
    wave: 2,
    details: 'Factory building layout and worker safety clearance under Factories Act 1948.'
  });

  res.json({
    success: true,
    totalServicesIdentified: recommendedServices.length,
    pollutionTier,
    evaluatedProfile: {
      projectType,
      industryType,
      district,
      isLandReq,
      landOwned,
      landArea,
      isElecReq,
      elecLoadKw,
      hasEmissions,
      hasHazWaste
    },
    services: recommendedServices,
    analysisBreakdown,
    prerequisitesList: prerequisites,
    executionWaves: [
      {
        waveNumber: 1,
        title: 'Wave 1: Prerequisite Resolution Gate',
        department: 'Land Revenue / Settlement Department',
        services: recommendedServices.filter(s => s.wave === 1),
        rule: 'MUST BE RESOLVED FIRST. All downstream departmental APIs block or wait if Land status is Pending/Under-Objection.'
      },
      {
        waveNumber: 2,
        title: 'Wave 2: Parallel Department Clearances',
        departments: 'MSEDCL (Electricity) & MPCB (Pollution Control)',
        services: recommendedServices.filter(s => s.wave === 2),
        rule: 'Executed concurrently once Wave 1 land identity and survey number are locked in the Canonical Model.'
      }
    ],
    guidanceNote: 'The Interoperability Platform Gateway will orchestrate these clearances across Land, Electricity, and Pollution departments with zero document resubmission.'
  });
});

export default router;
