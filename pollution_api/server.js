const express = require('express');
const morgan = require('morgan');

const pollutionRoutes = require('./routes/pollution');
const { notFoundHandler, errorHandler } = require('./middleware/errorHandler');

const app = express();
// Port and bind address come from the repo-root ports.json (single source of truth).
const PORTS = require('../ports.json');
const HOST = PORTS.host;
const PORT = PORTS.services.pollution.port;

const path = require('path');

// CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, X-API-Key, X-Correlation-ID');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

app.use(morgan('dev'));
app.use(express.json());

// Serve static frontend files
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/info', (req, res) => {
  res.json({
    service: 'Pollution / Environment Department API (simulated)',
    description:
      'A deliberately independent, legacy-shaped demo environmental API for consent and compliance verification in the Government Interoperability Layer.',
    endpoints: [
      'GET    /api/pollution/applications/:applicationNo',
      'GET    /api/pollution/status/:applicationNo',
      'POST   /api/pollution/verify',
      'PATCH  /api/pollution/applications/:applicationNo/consent',
      'POST   /api/pollution/schema-mapping/detect',
      'GET    /api/pollution/audit'
    ]
  });
});

app.use('/api/pollution', pollutionRoutes);

app.use(notFoundHandler);
app.use(errorHandler);

const server = app.listen(PORT, HOST, () => {
  console.log(`Pollution Department API (simulated) listening on http://${HOST}:${PORT}`);
  console.log('See README.md for demo API keys and example requests.');
});

// Fail loudly if the port from ports.json is taken (never drift to another port).
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`❌ Port ${PORT} on ${HOST} is already in use. Pollution Department API must run on the port in ports.json — stop the other process and try again.`);
  } else {
    console.error('Server error:', err);
  }
  process.exit(1);
});
