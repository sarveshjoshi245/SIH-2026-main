const { findConsumerByKey } = require('../config/consumers');

/**
 * requirePermission('verify') -> middleware that:
 *   - 401s if there's no X-API-Key header, or the key isn't recognized
 *   - 403s if the key is valid but lacks the required permission
 *   - otherwise attaches req.consumer and calls next()
 */
function requirePermission(permission) {
  return function authMiddleware(req, res, next) {
    const apiKey = req.header('X-API-Key');

    if (!apiKey) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Missing X-API-Key header. This is a protected government-style endpoint.'
      });
    }

    const consumer = findConsumerByKey(apiKey);

    if (!consumer) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'API key not recognized.'
      });
    }

    if (!consumer.permissions.includes(permission)) {
      return res.status(403).json({
        error: 'Forbidden',
        message: `Consumer '${consumer.consumerId}' is not permitted to call this endpoint (requires '${permission}').`
      });
    }

    req.consumer = { apiKey, ...consumer };
    next();
  };
}

module.exports = { requirePermission };
