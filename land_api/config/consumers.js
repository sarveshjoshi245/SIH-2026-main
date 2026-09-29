/**
 * Synthetic demo credentials for authorized machine-to-machine consumers.
 * These are NOT real government credentials — they only exist to
 * demonstrate authenticated, permission-scoped access as described
 * in the project write-up (Section 10: Authentication and Authorization).
 *
 * Each consumer is issued an API key and a set of permissions that
 * gate specific endpoints. A valid key with an unpermitted scope
 * still gets rejected (403), and no key at all gets rejected (401).
 */

const CONSUMERS = {
  'interop-demo-key-001': {
    consumerId: 'INTEROP-PLATFORM',
    description: 'The interoperability layer itself — full access for orchestration and audit review.',
    permissions: ['read:records', 'read:status', 'verify', 'admin:mutation', 'read:audit', 'detect:schema-drift']
  },
  'mpcb-demo-key-002': {
    consumerId: 'MPCB-CONSENT',
    description: 'Pollution Control Board consent system — only needs to check land prerequisites.',
    permissions: ['read:status', 'verify']
  },
  'discom-demo-key-003': {
    consumerId: 'ELECTRICITY-DISCOM',
    description: 'Electricity distribution company system — only needs coarse status, nothing else.',
    permissions: ['read:status']
  }
};

function findConsumerByKey(apiKey) {
  return CONSUMERS[apiKey] || null;
}

module.exports = { CONSUMERS, findConsumerByKey };
