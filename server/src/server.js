import http from 'http';
import { Server } from 'socket.io';
import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { initDatabase } from './db/database.js';
import authRoutes from './routes/authRoutes.js';
import landRoutes from './routes/landRoutes.js';
import interopRoutes from './routes/interopRoutes.js';
import portalRoutes from './routes/portalRoutes.js';
import adminRoutes from './routes/adminRoutes.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Ports and addresses come from the repo-root ports.json (single source of truth).
// Cloud / single-service overrides: Render (and most hosts) inject $PORT and
// require binding to 0.0.0.0. Set SINGLE_SERVICE=1 (see render.yaml) to make
// the browser use same-origin proxy paths instead of localhost URLs.
const PORTS = JSON.parse(fs.readFileSync(path.join(__dirname, '../../ports.json'), 'utf8'));
const SINGLE_SERVICE = process.env.SINGLE_SERVICE === '1' || Boolean(process.env.RENDER);
const HOST = process.env.HOST || (process.env.PORT ? '0.0.0.0' : PORTS.host);
const PORT = Number(process.env.PORT) || PORTS.services.portal.port;
// Internal addresses (inside one container/VM these are always localhost).
const interopInternal = process.env.INTEROP_BACKEND_URL || `http://127.0.0.1:${PORTS.services.interop.port}`;
const landInternal = process.env.LAND_API_URL || `http://127.0.0.1:${PORTS.services.land.port}`;
const electricityInternal = process.env.ELECTRICITY_API_URL || `http://127.0.0.1:${PORTS.services.electricity.port}`;
const pollutionInternal = process.env.POLLUTION_API_URL || `http://127.0.0.1:${PORTS.services.pollution.port}`;

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

app.set('io', io);

io.on('connection', (socket) => {
  console.log(`🔌 Socket.io client connected: ${socket.id}`);
  socket.on('disconnect', () => {
    console.log(`❌ Socket.io client disconnected: ${socket.id}`);
  });
});

app.use(cors());
app.use(express.json());

// Runtime config for the browser, generated from ports.json so the dashboard
// never hard-codes a backend address (it loads this before its own script).
// In SINGLE_SERVICE mode the browser cannot reach 127.0.0.1, so we publish
// same-origin proxy paths (see the /_interop + /dept-* proxies below).
app.get('/config.js', (req, res) => {
  const config = SINGLE_SERVICE
    ? {
        interopBackendUrl: '/_interop',
        landPortalUrl: '/dept-land',
        electricityPortalUrl: '/dept-electricity',
        pollutionPortalUrl: '/dept-pollution',
        singleService: true,
      }
    : { interopBackendUrl: `http://${PORTS.host}:${PORTS.services.interop.port}` };
  res.type('application/javascript').set('Cache-Control', 'no-store');
  res.send(`window.SAMANVAY_CONFIG = ${JSON.stringify(config)};\n`);
});

// ── Single-service reverse proxy (browser -> portal -> internal service) ──
// Lets ONE public web service expose all 5 services. No extra dependencies:
// uses the global fetch available in Node 18+. Only active paths are proxied;
// local multi-port development is unaffected.
async function proxyTo(req, res, targetBase, stripPrefix) {
  try {
    const suffix = req.originalUrl.slice(stripPrefix.length) || '/';
    const target = `${targetBase}${suffix.startsWith('/') ? suffix : `/${suffix}`}`;
    const headers = { ...req.headers };
    delete headers.host;
    delete headers.connection;
    delete headers['content-length'];
    const hasBody = !['GET', 'HEAD'].includes(req.method);
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? JSON.stringify(req.body) : undefined,
      redirect: 'manual',
    });
    const buf = Buffer.from(await upstream.arrayBuffer());
    const ct = upstream.headers.get('content-type');
    if (ct) res.set('content-type', ct);
    res.status(upstream.status).send(buf);
  } catch (err) {
    res.status(502).json({ success: false, message: `Internal service unavailable: ${err.message}`, retryable: true });
  }
}
// NOTE: express.json() must run before these so POST bodies are parsed.
app.use('/_interop', (req, res) => proxyTo(req, res, interopInternal, '/_interop'));
app.use('/dept-land', (req, res) => proxyTo(req, res, landInternal, '/dept-land'));
app.use('/dept-electricity', (req, res) => proxyTo(req, res, electricityInternal, '/dept-electricity'));
app.use('/dept-pollution', (req, res) => proxyTo(req, res, pollutionInternal, '/dept-pollution'));

// Serve static frontend files directly
app.use(express.static(path.join(__dirname, '../public')));

// Request logging
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  next();
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/land', landRoutes);
app.use('/api/interop', interopRoutes);
app.use('/api/portal', portalRoutes);
app.use('/api/admin', adminRoutes);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ONLINE',
    service: 'Government Interoperability Platform Core',
    database: 'SQLite (Persistent)',
    timestamp: new Date().toISOString()
  });
});

// Initialize database and start listening
initDatabase().then(() => {
  server.listen(PORT, HOST, () => {
    console.log(`=======================================================`);
    console.log(`🏛️  MAITRI Government Interoperability Platform Running!`);
    console.log(`📡 URL: http://${HOST}:${PORT}  (PORT env or ports.json, SINGLE_SERVICE=${SINGLE_SERVICE})`);
    console.log(`⚡ Real-time Socket.io server active.`);
    console.log(`💾 SQLite Database initialized and ready.`);
    console.log(`=======================================================`);
  });

  // Fail loudly instead of drifting to another port: the port is fixed in ports.json.
  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`❌ Port ${PORT} on ${HOST} is already in use. The portal must run on the port in ports.json — stop the other process and try again.`);
    } else {
      console.error('Server error:', err);
    }
    process.exit(1);
  });
}).catch(err => {
  console.error('Failed to initialize database:', err);
});
