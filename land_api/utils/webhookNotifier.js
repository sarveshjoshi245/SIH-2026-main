const crypto = require('crypto');

// Must match WEBHOOK_SECRET in interop_backend/app/routers/webhooks.py
// Portal address from the repo-root ports.json (single source of truth).
const PORTS = require('../../ports.json');
const GATEWAY_WEBHOOK_URL = `http://${PORTS.host}:${PORTS.services.portal.port}/api/webhooks/land-status-changed`;
const WEBHOOK_SECRET = process.env.GATEWAY_WEBHOOK_SECRET || 'GOV-INTEROP-SECRET-KEY';

function signPayload(payloadString) {
  return crypto.createHmac('sha256', WEBHOOK_SECRET).update(payloadString).digest('hex');
}

/**
 * Fire-and-forget notification to the interoperability gateway.
 * Called whenever an officer approves/rejects a mutation via the
 * PATCH /records/:surveyNumber/mutation endpoint. Delivery failure
 * here must never block the officer's own action — the gateway also
 * has a polling reconciliation path as a safety net in production.
 */
async function notifyGatewayOfMutationChange(record) {
  const payload = {
    survey_number: record.gtn,
    organization_pan: record.malak_pan,
    mutation_status: record.jamabandi,
    changed_at: new Date().toISOString(),
  };
  const payloadString = JSON.stringify(payload);
  const signature = signPayload(payloadString);

  const targetUrls = [GATEWAY_WEBHOOK_URL];

  for (const url of targetUrls) {
    try {
      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Signature': signature,
        },
        body: payloadString,
      });
    } catch (err) {
      // Ignore fallback url failures
    }
  }
}

module.exports = { notifyGatewayOfMutationChange };
