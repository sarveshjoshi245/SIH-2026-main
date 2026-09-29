function notFoundHandler(req, res) {
  res.status(404).json({
    error: 'Not Found',
    message: `No such endpoint: ${req.method} ${req.originalUrl}`
  });
}

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: 'Bad Request', message: 'Malformed JSON body.' });
  }
  console.error(err);
  res.status(500).json({ error: 'Internal Server Error', message: 'Something went wrong.' });
}

module.exports = { notFoundHandler, errorHandler };
