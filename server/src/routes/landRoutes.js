import express from 'express';
import { db } from '../db/seedData.js';

const router = express.Router();

// Middleware: Simulate Department API Key authorization
const verifyApiKey = (req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || apiKey !== 'GOV-INTEROP-SECRET-KEY') {
    return res.status(401).json({
      error: 'UNAUTHORIZED',
      message: 'Invalid or missing Department API Authorization Key (X-API-Key header required)'
    });
  }
  next();
};

let isSimulatedOutage = false;

// GET /api/land/verify/:surveyNo - Department Raw Legacy Record Endpoint
router.get('/verify/:surveyNo', verifyApiKey, (req, res) => {
  if (isSimulatedOutage) {
    return res.status(503).json({
      error: 'DEPARTMENT_SERVICE_UNAVAILABLE',
      retryable: true,
      message: 'Land Records Department Database undergoing routine maintenance. Please retry later.'
    });
  }

  const { surveyNo } = req.params;
  const record = db.landRecords[surveyNo];

  if (!record) {
    return res.status(404).json({
      error: 'NOT_FOUND',
      message: `Survey Number ${surveyNo} not found in Land Department records`
    });
  }

  db.auditLogs.push({
    id: `AUD-LAND-${Date.now()}`,
    timestamp: new Date().toISOString(),
    consumer: req.headers['x-consumer-id'] || 'INTEROP-PLATFORM',
    department: 'LAND_DEPARTMENT',
    surveyNumber: surveyNo,
    outcome: 'SUCCESS',
    httpStatus: 200
  });

  res.json({
    status: 'SUCCESS',
    department: 'Land Records Department, Govt. of Maharashtra',
    data: record
  });
});

// POST /api/land/update-mutation - Simulate Land Dept changing mutation status (e.g., PENDING -> APPROVED)
router.post('/update-mutation', verifyApiKey, (req, res) => {
  const { surveyNo, newStatus } = req.body;
  if (!db.landRecords[surveyNo]) {
    return res.status(404).json({ success: false, message: 'Survey number not found' });
  }

  db.landRecords[surveyNo].jamabandi = newStatus;
  db.landRecords[surveyNo].last_updated = new Date().toISOString();

  db.auditLogs.push({
    id: `AUD-LAND-MUT-${Date.now()}`,
    timestamp: new Date().toISOString(),
    department: 'LAND_DEPARTMENT',
    surveyNumber: surveyNo,
    event: 'MUTATION_STATUS_CHANGED',
    newStatus
  });

  res.json({
    success: true,
    message: `Land Record Jamabandi (Mutation) for Survey ${surveyNo} updated to ${newStatus}`,
    updatedRecord: db.landRecords[surveyNo]
  });
});

// POST /api/land/toggle-outage - Toggle simulated 503 outage for testing circuit breaker resilience
router.post('/toggle-outage', (req, res) => {
  isSimulatedOutage = !isSimulatedOutage;
  res.json({
    success: true,
    isOutageActive: isSimulatedOutage,
    message: isSimulatedOutage ? 'Land API Outage activated (503 Service Unavailable)' : 'Land API Restored (200 OK)'
  });
});

export default router;
