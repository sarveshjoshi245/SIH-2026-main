#!/usr/bin/env node
/*
 * start-single.js — run all 5 Samanvay services inside ONE web service/container.
 *
 * For Render / Railway single-service deploy. Only the portal port is public
 * ($PORT, 0.0.0.0). The other 4 services stay on localhost internal ports
 * from ports.json. The portal proxies them (/_interop, /dept-*) so the
 * browser never needs localhost.
 *
 *   SINGLE_SERVICE=1 node start-single.js
 *   PORT=10000 SINGLE_SERVICE=1 node start-single.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const ROOT = __dirname;
const PORTS = JSON.parse(fs.readFileSync(path.join(ROOT, 'ports.json'), 'utf8'));
const ORDER = ['land', 'pollution', 'electricity', 'interop', 'portal'];
const PUBLIC_PORT = Number(process.env.PORT) || PORTS.services.portal.port;

function pickPython(dir) {
  const cands = [
    path.join(dir, 'venv', 'Scripts', 'python.exe'),
    path.join(dir, '.venv', 'Scripts', 'python.exe'),
    path.join(dir, 'venv', 'bin', 'python'),
    path.join(dir, '.venv', 'bin', 'python'),
    'python', 'python3',
  ];
  for (const py of cands) {
    if (py.includes(path.sep) && !fs.existsSync(py)) continue;
    const r = spawnSync(py, ['-c', 'import uvicorn'], { cwd: dir, encoding: 'utf8' });
    if (r.status === 0) return py;
  }
  return 'python3';
}

function commandFor(name) {
  const dir = path.join(ROOT, PORTS.services[name].dir);
  if (name === 'portal') return { cmd: process.execPath, argv: ['src/server.js'], dir };
  if (name === 'land' || name === 'pollution') return { cmd: process.execPath, argv: ['server.js'], dir };
  return { cmd: pickPython(dir), argv: ['run_dev.py'], dir };
}

async function waitFor(name, timeoutMs = 90000) {
  const svc = PORTS.services[name];
  const port = name === 'portal' ? PUBLIC_PORT : svc.port;
  const url = `http://127.0.0.1:${port}${svc.health}`;
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
      const body = await res.text();
      let service = null;
      try { service = JSON.parse(body).service; } catch (e) { /* not JSON */ }
      if (service === svc.expect) {
        console.log(`✔ ${name} up on 127.0.0.1:${port} as "${service}"`);
        return;
      }
    } catch (e) { /* not up yet */ }
    if (Date.now() > deadline) throw new Error(`${name} did not answer at ${url} within ${timeoutMs / 1000}s`);
    await new Promise((r) => setTimeout(r, 800));
  }
}

(async () => {
  console.log(`Samanvay single-service mode — public portal port ${PUBLIC_PORT}, internal ports from ports.json`);
  const children = [];
  const env = { ...process.env, SINGLE_SERVICE: '1', PORT: String(PUBLIC_PORT), PYTHONUNBUFFERED: '1' };
  for (const name of ORDER) {
    const { cmd, argv, dir } = commandFor(name);
    const child = spawn(cmd, argv, { cwd: dir, stdio: 'inherit', env });
    child.on('exit', (code) => {
      console.error(`! ${name} exited (code ${code}) — stopping all`);
      for (const c of children) { try { c.kill('SIGTERM'); } catch (e) { /* gone */ } }
      process.exit(code ?? 1);
    });
    children.push(child);
    console.log(`started ${name} pid ${child.pid} in ${dir}`);
    await new Promise((r) => setTimeout(r, 1500));
  }
  for (const name of ORDER) await waitFor(name);
  console.log(`\nAll 5 services are up. Public URL: http://0.0.0.0:${PUBLIC_PORT}`);
  const stop = () => { console.log('\nStopping…'); for (const c of children) { try { c.kill('SIGTERM'); } catch (e) { /* gone */ } } process.exit(0); };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
  setInterval(() => {}, 1 << 30);
})().catch((err) => { console.error('Single-service startup failed:', err.message); process.exit(1); });
