const express = require('express');
const morgan = require('morgan');
const path = require('path');

const landRoutes = require('./routes/land');
const { notFoundHandler, errorHandler } = require('./middleware/errorHandler');

const app = express();
// Port and bind address come from the repo-root ports.json (single source of truth).
const PORTS = require('../ports.json');
const HOST = PORTS.host;
const PORT = PORTS.services.land.port;

app.use(morgan('dev'));
app.use(express.json());

// Serve the independent Land Department website
// Where Samanvay's portal runs (port from ports.json), for the Land website's
// "Return to Samanvay" button when the page was not opened from Samanvay.
app.get('/samanvay-config.js', (req, res) => {
  res.type('application/javascript').set('Cache-Control', 'no-store');
  res.send(`window.SAMANVAY_PORTAL_PORT = ${Number(PORTS.services.portal.port)};
`);
});

app.use(express.static(path.join(__dirname, 'public')));

// CORS for frontend
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

// Root serves the Land Department website (index.html via static middleware)
// API info endpoint moved to /api/land/info to avoid conflict
app.get('/api/land/info', (req, res) => {
  res.json({
    service: 'Land Records Department API (simulated)',
    description:
      'A deliberately legacy-shaped, independently-owned demo government API — the first departmental building block for the Government Interoperability Layer.',
    endpoints: [
      'GET    /api/land/records/:surveyNumber',
      'GET    /api/land/status/:surveyNumber',
      'POST   /api/land/verify',
      'PATCH  /api/land/records/:surveyNumber/mutation',
      'POST   /api/land/schema-mapping/detect',
      'GET    /api/land/audit'
    ]
  });
});

app.use('/api/land', landRoutes);

app.use(notFoundHandler);
app.use(errorHandler);

const server = app.listen(PORT, HOST, () => {
  console.log(`Land Department API (simulated) listening on http://${HOST}:${PORT}`);
  console.log('See README.md for demo API keys and example requests.');
});

// Fail loudly if the port from ports.json is taken (never drift to another port).
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`❌ Port ${PORT} on ${HOST} is already in use. Land Department API must run on the port in ports.json — stop the other process and try again.`);
  } else {
    console.error('Server error:', err);
  }
  process.exit(1);
});
