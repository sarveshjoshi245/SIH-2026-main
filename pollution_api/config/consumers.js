const consumers = [
  {
    consumerId: 'interop-platform',
    apiKey: 'interop-demo-key-001',
    permissions: [
      'read:applications',
      'read:status',
      'verify',
      'admin:consent',
      'detect:schema-drift',
      'read:audit'
    ]
  },
  {
    consumerId: 'interop-readonly',
    apiKey: 'interop-readonly-key-001',
    permissions: ['read:applications', 'read:status']
  }
];

function findConsumerByKey(apiKey) {
  return consumers.find((consumer) => consumer.apiKey === apiKey) || null;
}

module.exports = { findConsumerByKey };
