#!/usr/bin/env node
/*
 * start-all.js — start every local service on the port assigned in ports.json,
 * and refuse / fail loudly instead of letting ports drift.
 *
 *   node start-all.js                 start everything (keeps running; Ctrl+C stops all)
 *   node start-all.js --only land,portal
 *   node start-all.js --check         only check that every assigned port is free
 *   node start-all.js --verify        only check that the RIGHT service answers on each port
 *   node start-all.js --ports <file>  use another ports file (default: ./ports.json)
 *
 * Before starting, every assigned port is checked on 127.0.0.1, 0.0.0.0 and [::]
 * (Windows lets two processes bind the same port on different addresses, which
 * silently hides one of them). After starting, each service's identity endpoint
 * must answer with the expected service name, and each port must have exactly one
 * listener, on 127.0.0.1 only.
 */
'use strict';
const fs = require('fs');
const net = require('net');
const path = require('path');
const { spawn, spawnSync, execSync } = require('child_process');

const ROOT = __dirname;
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? (args[i + 1] || '') : null; };
const has = (name) => args.includes(name);
const PORTS_FILE = path.resolve(ROOT, opt('--ports') || 'ports.json');
const PORTS = JSON.parse(fs.readFileSync(PORTS_FILE, 'utf8'));
const HOST = PORTS.host;
const ORDER = ['land', 'pollution', 'electricity', 'interop', 'portal'];   // departments first, portal last
const only = opt('--only');
const selected = ORDER.filter((n) => PORTS.services[n] && (!only || only.split(',').map((s) => s.trim()).includes(n)));
const LOG_DIR = path.join(ROOT, 'logs', 'start-all');
const isWin = process.platform === 'win32';
const PIDS_FILE = path.join(LOG_DIR, 'pids.json');

// ── Kill previously-launched services (reload-cycle cleanup) ─────────────────
function isProcessAlive(pid) {
  try {
    if (isWin) {
      const out = execSync(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`, { encoding: 'utf8' }).trim();
      return out.length > 0 && !out.startsWith('INFO:');
    }
    process.kill(pid, 0);   // signal 0 = probe only
    return true;
  } catch (e) { return false; }
}
function stopPreviousRun() {
  if (!fs.existsSync(PIDS_FILE)) return;
  let prev;
  try { prev = JSON.parse(fs.readFileSync(PIDS_FILE, 'utf8')); } catch (e) { return; }
  const alive = Object.entries(prev).filter(([, pid]) => isProcessAlive(pid));
  if (!alive.length) return;
  console.log(`\nStopping ${alive.length} service(s) from previous run…`);
  for (const [svcName, pid] of alive) {
    try {
      if (isWin) spawnSync('taskkill', ['/PID', String(pid), '/T', '/F']);
      else process.kill(pid, 'SIGTERM');
      ok(`  stopped ${svcName.padEnd(12)} pid ${pid}`);
    } catch (e) {
      info(`  (${svcName} pid ${pid} already gone)`);
    }
  }
  // Give OS a moment to release ports after kill
  const t = Date.now() + 1500;
  while (Date.now() < t) { /* spin-wait */ }
}

// ── output helpers ──────────────────────────────────────────────────────────────
const RED = '\x1b[31m', GRN = '\x1b[32m', YEL = '\x1b[33m', BLD = '\x1b[1m', RST = '\x1b[0m';
const ok = (m) => console.log(`${GRN}✔${RST} ${m}`);
const info = (m) => console.log(`  ${m}`);
function fail(title, lines, code) {
  const bar = '█'.repeat(78);
  console.error(`\n${RED}${bar}\n█  ✖ ${BLD}${title}${RST}${RED}\n${bar}${RST}`);
  for (const l of lines) console.error(`${RED}   ${l}${RST}`);
  console.error('');
  stopChildren();
  process.exit(code);
}

// ── who is listening on a port? ─────────────────────────────────────────────────
function processName(pid) {
  try {
    if (isWin) {
      const out = execSync(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`, { encoding: 'utf8' }).trim();
      const m = out.match(/^"([^"]+)"/); return m ? m[1] : '?';
    }
    return execSync(`ps -p ${pid} -o comm=`, { encoding: 'utf8' }).trim() || '?';
  } catch (e) { return '?'; }
}
function listeners(port) {
  const found = [];
  try {
    if (isWin) {
      const out = execSync('netstat -ano', { encoding: 'utf8' });
      for (const line of out.split(/\r?\n/)) {
        const m = line.trim().match(/^TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)$/i);
        if (m && +m[2] === port) found.push({ addr: m[1], pid: +m[3] });
      }
    } else {
      const out = execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN -F pn || true`, { encoding: 'utf8' });
      let pid = null;
      for (const l of out.split('\n')) { if (l[0] === 'p') pid = +l.slice(1); if (l[0] === 'n') found.push({ addr: l.slice(1).replace(/:\d+$/, ''), pid }); }
    }
  } catch (e) { /* fall through to the connect probe */ }
  return found.map((f) => ({ ...f, name: processName(f.pid) }));
}
function canConnect(host, port) {
  return new Promise((resolve) => {
    const s = net.connect({ host, port });
    s.setTimeout(700);
    s.once('connect', () => { s.destroy(); resolve(true); });
    s.once('timeout', () => { s.destroy(); resolve(false); });
    s.once('error', () => resolve(false));
  });
}
const addrLabel = (a) => (a === '[::]' ? '[::] (all IPv6)' : a === '0.0.0.0' ? '0.0.0.0 (all IPv4)' : a);

// ── identity check ──────────────────────────────────────────────────────────────
async function identity(name) {
  const svc = PORTS.services[name];
  const url = `http://${HOST}:${svc.port}${svc.health}`;
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    const body = await res.text();
    let service = null;
    try { service = JSON.parse(body).service; } catch (e) { /* not JSON */ }
    return { url, status: res.status, service, body: body.slice(0, 120) };
  } catch (e) {
    return { url, status: null, error: e.cause ? e.cause.code || e.message : e.message };
  }
}
function whoIs(serviceName) {
  const hit = Object.entries(PORTS.services).find(([, s]) => s.expect === serviceName);
  return hit ? `the "${hit[0]}" service (assigned port ${hit[1].port})` : 'an unknown service';
}

// ── children ────────────────────────────────────────────────────────────────────
const children = [];
function stopChildren() {
  for (const c of children) { try { if (isWin) spawnSync('taskkill', ['/PID', String(c.pid), '/T', '/F']); else c.kill('SIGTERM'); } catch (e) { /* already gone */ } }
}
function pickPython(dir) {
  const cands = [path.join(dir, 'venv', 'Scripts', 'python.exe'), path.join(dir, '.venv', 'Scripts', 'python.exe'),
    path.join(dir, 'venv', 'bin', 'python'), path.join(dir, '.venv', 'bin', 'python'), 'python', 'python3'];
  for (const py of cands) {
    if (py.includes(path.sep) && !fs.existsSync(py)) continue;
    const r = spawnSync(py, ['-c', 'import app.main, uvicorn'], { cwd: dir, encoding: 'utf8' });
    if (r.status === 0) return py;
  }
  return null;
}
function commandFor(name) {
  const dir = path.join(ROOT, PORTS.services[name].dir);
  if (name === 'portal') return { cmd: process.execPath, argv: ['src/server.js'], dir };
  if (name === 'land' || name === 'pollution') return { cmd: process.execPath, argv: ['server.js'], dir };
  const py = pickPython(dir);
  if (!py) fail(`Cannot start "${name}": no Python found that can import its app`, [`Looked in ${dir}\\venv, .venv and the system python.`, 'Install its requirements (pip install -r requirements.txt) and try again.'], 3);
  return { cmd: py, argv: ['run_dev.py'], dir };
}
function tail(file, n = 12) { try { return fs.readFileSync(file, 'utf8').trim().split(/\r?\n/).slice(-n); } catch (e) { return []; } }

// ── main ────────────────────────────────────────────────────────────────────────
(async () => {
  console.log(`${BLD}Samanvay local services${RST} — ports from ${path.relative(ROOT, PORTS_FILE) || PORTS_FILE}, bind address ${HOST}\n`);

  // 0) Kill services from any previous start-all.js run (reload-cycle cleanup).
  if (!has('--check') && !has('--verify')) stopPreviousRun();

  if (has('--verify')) {
    const bad = [];
    for (const name of selected) {
      const svc = PORTS.services[name], r = await identity(name);
      if (r.status === null) bad.push(`${name} (port ${svc.port}): NOTHING ANSWERED at ${r.url} (${r.error})`);
      else if (r.service !== svc.expect) bad.push(`${name} (port ${svc.port}): WRONG SERVICE — expected "${svc.expect}", got "${r.service}"${r.service ? ` = ${whoIs(r.service)}` : ` (response: ${r.body})`}`);
      else ok(`${name.padEnd(12)} port ${svc.port}  answers as "${r.service}"`);
    }
    if (bad.length) fail('Wrong or missing service on an assigned port', bad, 2);
    return;
  }

  // 1) Refuse if any assigned port is already in use — on ANY address.
  const conflicts = [];
  for (const name of selected) {
    const port = PORTS.services[name].port;
    const ls = listeners(port);
    const v4 = await canConnect('127.0.0.1', port);
    const by = (addr) => ls.filter((l) => l.addr === addr);
    const describe = (addr) => { const x = by(addr); return x.length ? `IN USE by ${x.map((l) => `pid ${l.pid} (${l.name})`).join(', ')}` : 'free'; };
    info(`${name.padEnd(12)} port ${port}:  127.0.0.1 ${describe('127.0.0.1')}  |  0.0.0.0 ${describe('0.0.0.0')}  |  [::] ${describe('[::]')}`);
    if (ls.length || v4) {
      const who = ls.length ? ls.map((l) => `${addrLabel(l.addr)}:${port} — pid ${l.pid} (${l.name})`) : [`something accepted a connection on 127.0.0.1:${port}`];
      conflicts.push(`${name} needs port ${port}, but it is already in use:`, ...who.map((w) => `    • ${w}`));
    }
  }
  if (conflicts.length) fail('Refusing to start: assigned port(s) already in use', [...conflicts, '', 'Stop those processes (or run `node start-all.js --verify` if the right services are already running).', 'Nothing was started.'], 1);
  ok('All assigned ports are free on 127.0.0.1, 0.0.0.0 and [::].');
  if (has('--check')) return;

  // 2) Start each service; its own code reads its port from ports.json.
  fs.mkdirSync(LOG_DIR, { recursive: true });
  for (const name of selected) {
    const { cmd, argv, dir } = commandFor(name);
    const logFile = path.join(LOG_DIR, `${name}.log`);
    const out = fs.openSync(logFile, 'w');
    const child = spawn(cmd, argv, { cwd: dir, stdio: ['ignore', out, out], windowsHide: true, env: { ...process.env, PYTHONUNBUFFERED: '1' } });
    child.serviceName = name; child.logFile = logFile;
    child.on('exit', (code) => { child.exited = code; });
    children.push(child);
    info(`started ${name.padEnd(12)} pid ${child.pid}  (${path.basename(cmd)} ${argv.join(' ')})  log: ${path.relative(ROOT, logFile)}`);
  }
  fs.writeFileSync(PIDS_FILE, JSON.stringify(Object.fromEntries(children.map((c) => [c.serviceName, c.pid])), null, 2));

  // 3) Each service must answer on its port with the expected identity.
  for (const child of children) {
    const name = child.serviceName, svc = PORTS.services[name];
    const deadline = Date.now() + 90000;
    let r;
    for (;;) {
      if (child.exited !== undefined) fail(`"${name}" exited during startup (code ${child.exited})`, ['Last log lines:', ...tail(child.logFile).map((l) => '  | ' + l)], 2);
      r = await identity(name);
      if (r.status !== null) break;
      if (Date.now() > deadline) fail(`"${name}" did not answer on port ${svc.port} within 90 s`, [`Tried ${r.url}: ${r.error}`, 'Last log lines:', ...tail(child.logFile).map((l) => '  | ' + l)], 2);
      await new Promise((res) => setTimeout(res, 500));
    }
    if (r.service !== svc.expect) {
      fail(`WRONG SERVICE on port ${svc.port} (assigned to "${name}")`, [`Expected "${svc.expect}"`, `Got      "${r.service}"${r.service ? ` = ${whoIs(r.service)}` : ` (response: ${r.body})`}`, `Checked  ${r.url}`], 2);
    }
    ok(`${name.padEnd(12)} port ${svc.port}  answers as "${r.service}"`);
  }

  // 4) Exactly one listener per port, bound to 127.0.0.1 only.
  const shared = [];
  for (const child of children) {
    const port = PORTS.services[child.serviceName].port;
    const ls = listeners(port);
    if (ls.length && (ls.length !== 1 || ls[0].addr !== HOST)) shared.push(`${child.serviceName} port ${port}: ${ls.map((l) => `${addrLabel(l.addr)} pid ${l.pid} (${l.name})`).join('; ')}`);
  }
  if (shared.length) fail('A port is bound to more than one address or process', shared, 2);
  ok(`Every port has exactly one listener, bound to ${HOST} only.`);

  console.log(`\n${GRN}${BLD}All ${children.length} services are up.${RST} Press Ctrl+C to stop them all.`);
  const stop = () => {
    console.log('\nStopping all services…');
    stopChildren();
    try { fs.writeFileSync(PIDS_FILE, '{}'); } catch (e) { /* best-effort */ }
    process.exit(0);
  };
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
  for (const c of children) c.on('exit', (code) => { if (!c.stopping) { console.error(`${YEL}! ${c.serviceName} exited (code ${code}). See ${path.relative(ROOT, c.logFile)}${RST}`); } });
  setInterval(() => {}, 1 << 30);   // keep the parent alive while services run
})();
