const crypto = require('crypto');

// In-memory audit trail. A production system would persist this
// durably; for the demo, the last MAX_ENTRIES transactions are kept.
const MAX_ENTRIES = 500;
const auditLog = [];

function generateTransactionId() {
  return `LAND-TXN-${crypto.randomBytes(3).toString('hex').toUpperCase()}`;
}

/**
 * Records a transaction. Deliberately excludes PAN and any other
 * sensitive identifiers from the stored entry (Section 13:
 * sensitive identifiers should not be unnecessarily written into
 * logs in raw form).
 */
function recordTransaction({ consumerId, endpoint, surveyNumber, outcome, httpStatus, responseTimeMs }) {
  const entry = {
    transaction_id: generateTransactionId(),
    timestamp: new Date().toISOString(),
    consumer_id: consumerId || 'UNKNOWN',
    endpoint,
    survey_number: surveyNumber || null,
    outcome,
    http_status: httpStatus,
    response_time_ms: responseTimeMs
  };

  auditLog.push(entry);
  if (auditLog.length > MAX_ENTRIES) auditLog.shift();

  return entry;
}

function getRecentTransactions(limit = 50) {
  return auditLog.slice(-limit).reverse();
}

/**
 * Express middleware factory. Wraps res.json to capture the outcome
 * and status code, and logs on finish with accurate timing.
 */
function auditMiddleware(endpointLabel, getSurveyNumber) {
  return function (req, res, next) {
    const start = process.hrtime.bigint();
    let outcome = 'UNKNOWN';

    const originalJson = res.json.bind(res);
    res.json = (body) => {
      outcome = (body && (body.outcome || body.dependency_status || body.error)) || (res.statusCode < 400 ? 'SUCCESS' : 'ERROR');
      return originalJson(body);
    };

    res.on('finish', () => {
      const durationMs = Number(process.hrtime.bigint() - start) / 1e6;
      recordTransaction({
        consumerId: req.consumer ? req.consumer.consumerId : null,
        endpoint: endpointLabel,
        surveyNumber: getSurveyNumber ? getSurveyNumber(req) : null,
        outcome,
        httpStatus: res.statusCode,
        responseTimeMs: Math.round(durationMs)
      });
    });

    next();
  };
}

module.exports = { recordTransaction, getRecentTransactions, auditMiddleware };
