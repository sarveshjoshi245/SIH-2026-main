import express from 'express';
import {
  submitDeptApplication,
  getDeptApplicationsByPan,
  getAllDeptApplications,
  updateDeptApplicationStatus,
  getAllDepartments,
  registerNewDepartment,
  getAllSchemaMappings,
  autoMapDepartmentSchema
} from '../db/database.js';

const router = express.Router();

// Simple admin token (in production, use JWT + role-based auth)
const ADMIN_PASSWORD = 'admin@sih2026';

function isAdmin(req) {
  const auth = req.headers['x-admin-token'] || req.query.adminToken;
  return auth === ADMIN_PASSWORD;
}

// ─────────────────────────────────────────────────────────────
// PUBLIC: Citizen submits an application to a department
// POST /api/admin/submit
// ─────────────────────────────────────────────────────────────
router.post('/submit', (req, res) => {
  const { department, citizenName, citizenPan, projectName, projectType, district, refNumber } = req.body;

  if (!department || !citizenName || !citizenPan || !projectName || !projectType) {
    return res.status(400).json({ success: false, message: 'department, citizenName, citizenPan, projectName and projectType are required.' });
  }

  const registeredDepts = getAllDepartments().map(d => d.dept_code.toUpperCase());
  const validDepts = Array.from(new Set(['LAND', 'ELECTRICITY', 'POLLUTION', ...registeredDepts]));
  if (!validDepts.includes(department.toUpperCase())) {
    return res.status(400).json({ success: false, message: `Invalid department. Registered options: ${validDepts.join(', ')}` });
  }

  try {
    const result = submitDeptApplication({
      department: department.toUpperCase(),
      citizenName,
      citizenPan: citizenPan.toUpperCase(),
      projectName,
      projectType,
      district,
      refNumber
    });

    const io = req.app.get('io');
    if (io) {
      io.emit('applicationSubmitted', {
        refNo: result.refNo,
        department: department.toUpperCase(),
        citizenPan: citizenPan.toUpperCase(),
        status: result.status
      });
    }

    return res.json({
      success: true,
      message: `Your application has been submitted to the ${department} department.`,
      refNo: result.refNo,
      status: result.status
    });
  } catch (err) {
    console.error('[admin/submit] error:', err.message);
    return res.status(500).json({ success: false, message: 'Failed to submit application.' });
  }
});

// ─────────────────────────────────────────────────────────────
// PUBLIC: Citizen checks their application status by PAN
// GET /api/admin/my-applications?pan=ABCDE1234F
// ─────────────────────────────────────────────────────────────
router.get('/my-applications', (req, res) => {
  const { pan } = req.query;
  if (!pan) return res.status(400).json({ success: false, message: 'pan query parameter is required.' });

  try {
    const apps = getDeptApplicationsByPan(pan.trim().toUpperCase());
    return res.json({ success: true, applications: apps });
  } catch (err) {
    return res.status(500).json({ success: false, message: 'Error fetching applications.' });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN: List all applications (optionally filter by department)
// GET /api/admin/applications?department=LAND   (needs x-admin-token header)
// ─────────────────────────────────────────────────────────────
router.get('/applications', (req, res) => {
  if (!isAdmin(req)) {
    return res.status(401).json({ success: false, message: 'Unauthorized. Provide x-admin-token header.' });
  }

  const { department } = req.query;
  try {
    const apps = getAllDeptApplications(department ? department.toUpperCase() : null);
    return res.json({ success: true, applications: apps, total: apps.length });
  } catch (err) {
    return res.status(500).json({ success: false, message: 'Error fetching applications.' });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN: Approve or reject a specific application
// POST /api/admin/review   (needs x-admin-token header)
// Body: { refNo, action: "APPROVED"|"REJECTED", remarks, reviewedBy }
// ─────────────────────────────────────────────────────────────
router.post('/review', (req, res) => {
  if (!isAdmin(req)) {
    return res.status(401).json({ success: false, message: 'Unauthorized. Provide x-admin-token header.' });
  }

  const { refNo, action, remarks, reviewedBy } = req.body;

  if (!refNo || !action) {
    return res.status(400).json({ success: false, message: 'refNo and action (APPROVED or REJECTED) are required.' });
  }

  if (!['APPROVED', 'REJECTED'].includes(action.toUpperCase())) {
    return res.status(400).json({ success: false, message: 'action must be APPROVED or REJECTED.' });
  }

  try {
    const updated = updateDeptApplicationStatus(refNo, action.toUpperCase(), remarks, reviewedBy || 'Dept Admin');
    if (!updated || updated.error) {
      return res.status(400).json({ success: false, message: updated?.error || `No application found with ref_no: ${refNo}` });
    }

    const io = req.app.get('io');
    if (io) {
      io.emit('applicationUpdated', {
        refNo: updated.ref_no,
        department: updated.department,
        citizenPan: updated.citizen_pan,
        status: updated.status,
        adminRemarks: updated.admin_remarks,
        application: updated
      });
    }

    return res.json({
      success: true,
      message: `Application ${refNo} has been ${action.toUpperCase()}.`,
      application: updated
    });
  } catch (err) {
    console.error('[admin/review] error:', err.message);
    return res.status(500).json({ success: false, message: 'Failed to update application status.' });
  }
});

// ─────────────────────────────────────────────────────────────
// ADMIN: Bulk approve or reject applications
// POST /api/admin/bulk-review
// Body: { refNos: [...], action: "APPROVED"|"REJECTED", remarks }
// ─────────────────────────────────────────────────────────────
router.post('/bulk-review', (req, res) => {
  if (!isAdmin(req)) {
    return res.status(401).json({ success: false, message: 'Unauthorized. Provide x-admin-token header.' });
  }

  const { refNos, action, remarks } = req.body;
  if (!Array.isArray(refNos) || refNos.length === 0 || !action) {
    return res.status(400).json({ success: false, message: 'refNos (array) and action (APPROVED or REJECTED) are required.' });
  }

  const updatedList = [];
  const io = req.app.get('io');
  for (const refNo of refNos) {
    const updated = updateDeptApplicationStatus(refNo, action.toUpperCase(), remarks, 'Dept Admin');
    if (updated && !updated.error) {
      updatedList.push(updated);
      if (io) {
        io.emit('applicationUpdated', {
          refNo: updated.ref_no,
          department: updated.department,
          citizenPan: updated.citizen_pan,
          status: updated.status,
          adminRemarks: updated.admin_remarks,
          application: updated
        });
      }
    }
  }

  return res.json({
    success: true,
    message: `${updatedList.length} applications have been ${action.toUpperCase()}.`,
    count: updatedList.length
  });
});

// ─────────────────────────────────────────────────────────────
// ADMIN: Verify admin password (login)
// POST /api/admin/login
// Body: { password }
// ─────────────────────────────────────────────────────────────
router.post('/login', (req, res) => {
  const { password } = req.body;
  if (password === ADMIN_PASSWORD) {
    return res.json({ success: true, token: ADMIN_PASSWORD, message: 'Admin authenticated.' });
  }
  return res.status(401).json({ success: false, message: 'Invalid admin password.' });
});

// ─────────────────────────────────────────────────────────────
// DYNAMIC DEPARTMENTS & AUTO SCHEMA MAPPER
// ─────────────────────────────────────────────────────────────

// GET /api/admin/departments (Public / Admin department list & schema mappings)
router.get('/departments', (req, res) => {
  try {
    const depts = getAllDepartments();
    const mappings = getAllSchemaMappings();
    return res.json({ success: true, departments: depts, mappings: mappings });
  } catch (err) {
    return res.status(500).json({ success: false, message: 'Failed to fetch departments.' });
  }
});

// POST /api/admin/departments/auto-map-schema
router.post('/departments/auto-map-schema', (req, res) => {
  const { samplePayload, deptCode } = req.body;
  if (!samplePayload) {
    return res.status(400).json({ success: false, message: 'samplePayload is required.' });
  }

  try {
    const suggestions = autoMapDepartmentSchema(samplePayload, deptCode);
    return res.json({ success: true, suggestions: suggestions, total: suggestions.length });
  } catch (err) {
    return res.status(500).json({ success: false, message: 'Auto schema mapping failed.' });
  }
});

// POST /api/admin/departments/register
router.post('/departments/register', (req, res) => {
  const { deptCode, deptName, category, endpointUrl, apiPort, serviceName, description, mappings } = req.body;

  if (!deptCode || !deptName || !endpointUrl) {
    return res.status(400).json({ success: false, message: 'deptCode, deptName, and endpointUrl are required.' });
  }

  try {
    const result = registerNewDepartment({
      deptCode,
      deptName,
      category,
      endpointUrl,
      apiPort,
      serviceName,
      description,
      mappings
    });

    const io = req.app.get('io');
    if (io) {
      io.emit('departmentRegistered', {
        deptCode: deptCode.toUpperCase(),
        deptName,
        category,
        endpointUrl
      });
    }

    return res.json({
      success: true,
      message: `Department '${deptName}' (${deptCode.toUpperCase()}) successfully registered and schema mapped!`,
      deptCode: deptCode.toUpperCase()
    });
  } catch (err) {
    console.error('Department registration error:', err.message);
    return res.status(500).json({ success: false, message: err.message || 'Department registration failed.' });
  }
});

export default router;
