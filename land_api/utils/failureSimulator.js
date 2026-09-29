/**
 * Lets a demo deliberately trigger a retryable 503 so the
 * interoperability layer's retry/circuit-breaker logic has
 * something real to react to (Section 12: Fault Tolerance).
 *
 * Triggers on any of:
 *   - header "X-Simulate-Failure: true"
 *   - query string "?simulateFailure=true"
 *   - the record itself being flagged simulateOutage: true (survey 999)
 */
function shouldSimulateFailure(req, record) {
  if (req.header('X-Simulate-Failure') === 'true') return true;
  if (req.query.simulateFailure === 'true') return true;
  if (record && record.simulateOutage) return true;
  return false;
}

function sendSimulatedOutage(res) {
  res.set('Retry-After', '5');
  return res.status(503).json({
    error: 'Service Unavailable',
    message: 'Land Department temporarily unavailable. Your application has not been lost — please retry.',
    retryable: true
  });
}

module.exports = { shouldSimulateFailure, sendSimulatedOutage };
