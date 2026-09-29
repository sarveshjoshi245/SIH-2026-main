const handoff = (() => {
  const p = new URLSearchParams(window.location.search);
  return {
    appId: p.get('app_id'),
    callback: p.get('callback'),
    pan: (p.get('pan') || '').toUpperCase(),
    applicant: p.get('applicant') || p.get('company') || '',
  };
})();

const SAMANVAY_PORTAL_PORT = window.SAMANVAY_PORTAL_PORT || 5001;
const SAMANVAY_ORIGIN = (() => {
  try { if (handoff.callback) return new URL(handoff.callback).origin; } catch (e) { /* bad callback */ }
  return `${window.location.protocol}//${window.location.hostname}:${SAMANVAY_PORTAL_PORT}`;
})();
const SAMANVAY_API = `${SAMANVAY_ORIGIN}/api/portal`;
let currentCallbackUrl = handoff.callback;
let lastApplicationRef = '';

function switchTab(tabId) {
  const tabs = ['status', 'category', 'apply', 'notice', 'database'];
  tabs.forEach(t => {
    const navEl = document.getElementById(`nav-${t}`);
    const secEl = document.getElementById(`section-${t}`);
    if (navEl) navEl.classList.toggle('active', t === tabId);
    if (secEl) secEl.style.display = (t === tabId) ? 'block' : 'none';
  });

  if (tabId === 'notice') renderNoticeTab();
  if (tabId === 'database') renderDatabaseTab();
}

async function fetchPollProfile() {
  const panEl = document.getElementById('pan');
  const panFromUrl = handoff.pan || '';
  const pan = (panEl?.value || panFromUrl || '').trim().toUpperCase();

  if (!pan || pan.length < 10) {
    alert('Please enter a valid 10-character PAN number first.');
    return;
  }

  const bar = document.getElementById('pollAutoFillBar');
  const msg = document.getElementById('pollAutoFillMsg');
  if (bar) bar.style.display = 'block';
  if (msg) msg.textContent = '🔄 Fetching profile from database...';

  try {
    const res = await fetch(`${SAMANVAY_API}/user-profile?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();

    if (data.success && data.found) {
      const p = data.profile;
      const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
      setVal('pan', p.pan);
      setVal('companyName', p.organization_name || p.full_name);

      if (msg) msg.innerHTML = `✅ Profile auto-filled for <strong>${p.organization_name || p.full_name}</strong>. All fields editable.`;
      if (bar) {
        bar.style.background = '#f0fdf4';
        bar.style.borderColor = '#86efac';
        bar.style.color = '#15803d';
      }
    } else {
      if (msg) msg.textContent = `⚠️ ${data.message || 'No profile found. Fill manually.'}`;
    }
  } catch (err) {
    // Silently hide the bar if form already has data from URL params
    if (bar) bar.style.display = 'none';
  }
}

function presetPollLookup(query) {
  const input = document.getElementById('pollQuery');
  if (input) {
    input.value = query;
    handleSearchPoll(new Event('submit'));
  }
}

async function handleSearchPoll(e) {
  if (e) e.preventDefault();
  const q = document.getElementById('pollQuery').value.trim();
  const resultDiv = document.getElementById('resultPoll');
  if (!q) return;

  resultDiv.innerHTML = '<div style="padding: 20px; text-align: center; color: #4f6e5c;">🔄 Fetching DPCC environmental consent facts...</div>';

  try {
    const res = await fetch(`/api/pollution/applications/${q}`, {
      headers: { 'X-API-Key': 'interop-demo-key-001' }
    });

    if (!res.ok) {
      resultDiv.innerHTML = `
        <div class="pol-card" style="padding: 24px; border-left: 4px solid #ef4444;">
          <h3 style="color: #dc2626; margin-bottom: 8px;">⚠️ Record Not Found</h3>
          <p style="font-size: 0.9rem; color: #4f6e5c;">No pollution consent record found for query "<strong>${q}</strong>".</p>
          <p style="font-size: 0.85rem; margin-top: 10px;">Try presets like <code>MPCB-8821</code> or submit a new application in the <strong>Apply</strong> tab.</p>
        </div>
      `;
      return;
    }

    const data = await res.json();
    renderPollSheet(data);
  } catch (err) {
    resultDiv.innerHTML = `<div style="padding: 20px; color: #dc2626;">❌ Error connecting to Pollution API: ${err.message}</div>`;
  }
}

function renderPollSheet(data) {
  const div = document.getElementById('resultPoll');
  const appNo = data.application_no || data.applicationNo || 'MPCB-8821';
  const name = data.industry_name || data.industryName || 'Enterprise Applicant';
  const pan = data.industry_pan || data.industryPan || 'ABCDE1234F';
  const category = data.air_emission_category || 'GREEN';
  const consentType = data.consent_type || 'CTE';
  const status = data.consent_status || 'APPROVED';
  const compliance = data.compliance_status || 'COMPLIANT';
  const location = data.plant_location || 'MIDC Chakan, Pune';
  const validUntil = data.valid_until || '2029-03-31';

  const statusBadge = status === 'APPROVED'
    ? '<span style="background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 4px; font-weight: 700;">APPROVED & COMPLIANT</span>'
    : '<span style="background: #fef9c3; color: #854d0e; padding: 4px 10px; border-radius: 4px; font-weight: 700;">PENDING EVALUATION</span>';

  div.innerHTML = `
    <div class="poll-sheet">
      <div class="poll-watermark">STATE POLLUTION CONTROL BOARD</div>

      <div class="poll-header-sheet">
        <h2 style="color: #14422b; font-size: 1.3rem;">SAMANVAY POLLUTION CONTROL DEPARTMENT</h2>
        <h3 style="font-size: 1.05rem; color: #1f2937;">ENVIRONMENTAL CONSENT TO ESTABLISH / OPERATE CERTIFICATE</h3>
        <p style="font-size: 0.85rem; color: #4f6e5c;">Department of Environment • State Pollution Control Board</p>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <div><strong>Application Ref:</strong> <code>${appNo}</code></div>
        <div><strong>Consent Status:</strong> ${statusBadge}</div>
      </div>

      <table class="poll-table">
        <tr>
          <th>Enterprise Name</th>
          <td><strong>${name}</strong></td>
          <th>Enterprise PAN</th>
          <td><code>${pan}</code></td>
        </tr>
        <tr>
          <th>Consent Type</th>
          <td><strong>${consentType}</strong> (Consent to Establish)</td>
          <th>Pollution Category</th>
          <td><span style="color: #15803d; font-weight: 700;">${category} CATEGORY</span></td>
        </tr>
        <tr>
          <th>Plant Location</th>
          <td>${location}</td>
          <th>Consent Validity</th>
          <td><strong>${validUntil}</strong></td>
        </tr>
        <tr>
          <th>Compliance Record</th>
          <td><strong style="color: #166534;">${compliance}</strong></td>
          <th>Clearance Type</th>
          <td>Single-Window Fast Track</td>
        </tr>
      </table>

      <div style="margin-top: 16px; background: #f0fdf4; padding: 12px; border-radius: 6px; font-size: 0.85rem; color: #166534;">
        🌿 <strong>Environmental Facts Verified:</strong> Zero trade effluent discharge verified. Air emission norms satisfied under Water (Prevention and Control of Pollution) Act 1974.
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; font-size: 0.8rem; color: #4f6e5c;">
        <div>Digitally authorized by Member Secretary (State Pollution Control Board)</div>
        <button onclick="window.print()" class="pol-btn pol-btn-outline" style="padding: 4px 12px; font-size: 0.8rem;">🖨️ Print Consent Certificate</button>
      </div>
    </div>
  `;
}

let pollAdminPollTimer = null;

async function handleApplyPollSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('companyName').value.trim();
  const pan = document.getElementById('pan').value.trim().toUpperCase();
  const category = document.getElementById('industryCategory').value;
  const consentType = document.getElementById('consentType').value;
  const location = document.getElementById('location').value.trim();

  const refNumber = `MPCB-2026-${Math.floor(1000 + Math.random() * 9000)}`;

  let adminRefNo = '';
  const portalOrigin = SAMANVAY_ORIGIN;

  try {
    const adminRes = await fetch(`${portalOrigin}/api/admin/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        department: 'POLLUTION',
        citizenName: name,
        citizenPan: pan,
        projectName: `Consent to Establish (${consentType}) - ${category}`,
        projectType: 'POLLUTION_CONSENT',
        district: 'Pune',
        refNumber: refNumber
      })
    });
    const adminData = await adminRes.json();
    if (adminData.success) adminRefNo = adminData.refNo;
  } catch (err) {
    console.warn('Admin queue submit error:', err);
  }

  try {
    await fetch('/api/pollution/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        applicationNo: refNumber,
        industryName: name,
        industryPan: pan,
        plantLocation: location,
        industryType: category,
        consentType: consentType
      })
    });
  } catch (err) {
    console.warn('Pollution backend apply notice:', err);
  }

  const activeRef = adminRefNo || refNumber;
  lastApplicationRef = activeRef;

  const banner = document.getElementById('submissionSuccessBanner');
  renderPollStatusPending(banner, activeRef);

  if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
  pollAdminPollTimer = setInterval(() => pollPollAdminStatus(pan, activeRef), 3000);
  pollPollAdminStatus(pan, activeRef);
}

function renderPollStatusPending(banner, refNo) {
  if (!banner) return;
  lastApplicationRef = refNo;
  banner.style.background = '#fff8e1';
  banner.style.borderColor = '#f59e0b';
  banner.style.color = '#78350f';
  banner.style.padding = '18px';
  banner.style.borderRadius = '10px';
  banner.style.display = 'block';

  banner.innerHTML = `
    <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
      <span>⏳</span> <span>अर्जाची स्थिती: प्रलंबित (Status: PENDING ADMIN APPROVAL)</span>
    </div>
    <div style="font-size: 0.88rem; margin-top: 6px;">अर्ज संदर्भ क्रमांक (Ref): <strong>${refNo}</strong></div>
    <div style="font-size: 0.84rem; color: #92400e; margin-top: 6px;">
      तुमचा पर्यावरण संमती अर्ज <a href="${SAMANVAY_ORIGIN}/admin.html" target="_blank" style="color: #1e3a8a; font-weight: 700;">/admin.html</a> मध्ये तपासणीखाली आहे. प्रशासकाकडून मंजुरी मिळाल्यावरच 'समन्वय पोर्टलवर परत जा' बटण उघडेल.
    </div>
  `;
}

function renderPollApprovedDetails(app, banner) {
  if (!banner) return;
  const refNo = app.ref_no || app.refNumber || 'MPCB-2026-001';
  const name = app.citizen_name || app.citizenName || 'Applicant Enterprise';
  const pan = app.citizen_pan || app.citizenPan || 'PAN0000000';
  const dist = app.district || 'Pune';
  const remarks = app.admin_remarks || '✓ Environmental Consent (CTE) granted with zero effluent discharge compliance.';

  lastApplicationRef = refNo;

  banner.style.background = '#ffffff';
  banner.style.border = '2px solid #166534';
  banner.style.display = 'block';
  banner.style.padding = '22px';
  banner.style.borderRadius = '12px';
  banner.style.boxShadow = '0 8px 24px rgba(0,0,0,0.06)';

  banner.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
      <div>
        <div style="font-size: 1.15rem; font-weight: 800; color: #166534; display: flex; align-items: center; gap: 8px;">
          <span>🌿</span> <span>प्रदूषण नियंत्रण मंडळ (State Pollution Control Board)</span>
        </div>
        <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">पर्यावरणीय संमती (Consent to Establish/Operate) — अधिकृत मान्यता पत्र</div>
      </div>
      <span style="background: #dcfce7; color: #15803d; border: 1px solid #86efac; font-weight: 800; font-size: 0.85rem; padding: 6px 14px; border-radius: 9999px;">
        ✓ ACCEPTED & APPROVED
      </span>
    </div>

    <div style="font-size: 0.88rem; margin-bottom: 12px; color: #1e293b; font-weight: 700;">अर्जाचे तपशील (Application Details):</div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 18px;">
      <div>
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">अर्ज संदर्भ क्र. (Ref No)</div>
        <div style="font-weight: 800; font-size: 0.95rem; color: #0f172a; font-family: monospace;">${refNo}</div>
      </div>
      <div>
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">उद्योगाचे नाव (Enterprise)</div>
        <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a;">${name}</div>
      </div>
      <div>
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">पॅन क्रमांक (PAN)</div>
        <div style="font-weight: 800; font-size: 0.9rem; color: #0f172a; font-family: monospace;">${pan}</div>
      </div>
      <div>
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">जिल्हा / क्षेत्र (District)</div>
        <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a;">${dist}</div>
      </div>
      <div>
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">प्रशासकीय निर्णय (Decision)</div>
        <div style="font-weight: 800; font-size: 0.9rem; color: #166534;">APPROVED</div>
      </div>
    </div>

    <div style="background: #f0fdf4; border-left: 4px solid #166534; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 6px 6px 0; font-size: 0.88rem; color: #166534;">
      💬 <strong>प्रशासकीय टीप (Admin Remark):</strong> ${remarks}
    </div>

    <div style="text-align: center; margin-top: 10px;">
      <button type="button" class="pol-btn pol-btn-primary" onclick="returnToSamanvay()" style="background: #166534; color: #ffffff; font-size: 1.05rem; font-weight: 800; padding: 14px 28px; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 6px 20px rgba(22,101,52,0.3); display: inline-flex; align-items: center; gap: 10px; width: 100%; justify-content: center;">
        ↩ <span>समन्वय पोर्टलवर परत जा (Return to Samanvay Portal ➔)</span>
      </button>
    </div>
  `;
}

function returnToSamanvay() {
  const ref = lastApplicationRef || ('MPCB-' + Date.now().toString().slice(-6));
  const url = `${SAMANVAY_ORIGIN}/dashboard.html?tab=flowchart&land_status=COMPLETED&electricity_status=COMPLETED&pollution_status=COMPLETED&pollution_ref=${encodeURIComponent(ref)}`;
  window.location.href = url;
}

async function pollPollAdminStatus(pan, refNo) {
  if (!pan || !refNo) return;
  const portalOrigin = SAMANVAY_ORIGIN;
  try {
    const res = await fetch(`${portalOrigin}/api/admin/my-applications?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();
    if (!data.success || !data.applications) return;

    const app = data.applications.find(a => a.ref_no === refNo || a.department === 'POLLUTION');
    if (!app) return;

    const banner = document.getElementById('submissionSuccessBanner');

    if (app.status === 'APPROVED') {
      if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
      renderPollApprovedDetails(app, banner);
    } else if (app.status === 'REJECTED') {
      if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
      if (banner) {
        banner.style.background = '#fef2f2';
        banner.style.borderColor = '#ef4444';
        banner.style.color = '#991b1b';
        banner.style.display = 'block';
        banner.style.padding = '18px';
        banner.style.borderRadius = '10px';
        banner.innerHTML = `
          <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
            <span>❌</span> <span>अर्जाची स्थिती: अयशस्वी / नामंजूर (Status: FAILED / REJECTED)</span>
          </div>
          <div style="font-size: 0.88rem; margin-top: 6px;">कारण: <strong>${app.admin_remarks || 'पर्यावरणीय मापदंड जुळले नाहीत.'}</strong></div>
          <div style="margin-top: 14px;">
            <button type="button" class="pol-btn" style="background: #dc3545; color: white; font-weight: 700; font-size: 0.88rem; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer;" onclick="reapplyPoll()">
              🔄 माहिती दुरुस्त करून पुन्हा अर्ज करा (Failed - Reapply Application)
            </button>
          </div>
        `;
      }
    }
  } catch (e) {}
}

function reapplyPoll() {
  if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
  const banner = document.getElementById('submissionSuccessBanner');
  if (banner) banner.style.display = 'none';
  switchTab('apply');
  document.getElementById('companyName').focus();
}

async function checkExistingPollAdminStatus(pan) {
  const banner = document.getElementById('submissionSuccessBanner');
  try {
    const res = await fetch(`${SAMANVAY_ORIGIN}/api/admin/my-applications?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();
    if (data.success && data.applications) {
      const app = data.applications.find(a => a.department === 'POLLUTION');
      if (app) {
        if (app.status === 'APPROVED') {
          renderPollApprovedDetails(app, banner);
        } else if (app.status === 'PENDING') {
          // Don't show pending banner — keep polling silently in background
          if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
          pollAdminPollTimer = setInterval(() => pollPollAdminStatus(pan, app.ref_no), 3000);
        }
      }
    }
  } catch (e) {}
}

function startSamanvayHandoff() {
  switchTab('apply');
  const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
  if (handoff.appId) setVal('appId', handoff.appId);
  if (handoff.pan) setVal('pan', handoff.pan);
  if (handoff.applicant) setVal('companyName', handoff.applicant);

  if (handoff.pan) {
    fetchPollProfile();
    checkExistingPollAdminStatus(handoff.pan);
  }
}

function renderNoticeTab() {
  const div = document.getElementById('resultNotice');
  div.innerHTML = `
    <div style="font-size: 0.95rem; color: #1b2e23;">
      <h3 style="color: var(--pol-green); margin-bottom: 12px;">🌿 Maharashtra Pollution Control Board (MPCB) Notices</h3>
      <ul style="margin-left: 20px; line-height: 1.8;">
        <li><strong>Green Category Fast-Track:</strong> Industrial CTE applications in Green category processed within 48 hours.</li>
        <li><strong>Air Quality Index (AQI) Compliance:</strong> Industrial boiler stack monitoring digitized across Okhla & Narela zones.</li>
      </ul>
    </div>
  `;
}

function renderDatabaseTab() {
  const div = document.getElementById('resultDatabase');
  div.innerHTML = `
    <div style="font-size: 0.9rem;">
      <p style="margin-bottom: 12px; color: #4f6e5c;">Maharashtra Pollution Control Board (MPCB) API endpoints available for SAMANVAY Interoperability Layer:</p>
      <pre style="background: #0d281a; color: #a5d6a7; padding: 14px; border-radius: 6px; font-family: monospace;">
GET  /api/pollution/applications/:applicationNo
GET  /api/pollution/status/:applicationNo
POST /api/pollution/verify
POST /api/pollution/apply
      </pre>
    </div>
  `;
}

let pollSocket = null;

function initPollSocket() {
  const portalOrigin = SAMANVAY_ORIGIN || 'http://127.0.0.1:5001';
  const setupConnection = () => {
    if (pollSocket || !window.io) return;
    try {
      pollSocket = io(portalOrigin);
      pollSocket.on('applicationUpdated', (data) => {
        if (!data) return;
        const currentPan = handoff.pan || (document.getElementById('pan')?.value || '').toUpperCase();
        if (data.department === 'POLLUTION' && (data.citizenPan === currentPan || data.refNo === lastApplicationRef)) {
          const banner = document.getElementById('submissionSuccessBanner');
          if (data.status === 'APPROVED') {
            if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
            renderPollApprovedDetails(data.application || data, banner);
          } else if (data.status === 'REJECTED') {
            if (pollAdminPollTimer) clearInterval(pollAdminPollTimer);
            if (banner) {
              banner.style.background = '#fef2f2';
              banner.style.borderColor = '#ef4444';
              banner.style.color = '#991b1b';
              banner.style.display = 'block';
              banner.style.padding = '18px';
              banner.style.borderRadius = '10px';
              banner.innerHTML = `
                <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
                  <span>❌</span> <span>अर्जाची स्थिती: अयशस्वी / नामंजूर (Status: FAILED / REJECTED)</span>
                </div>
                <div style="font-size: 0.88rem; margin-top: 6px;">कारण: <strong>${data.adminRemarks || 'पर्यावरणीय मापदंड जुळले नाहीत.'}</strong></div>
                <div style="margin-top: 14px;">
                  <button type="button" class="pol-btn" style="background: #dc3545; color: white; font-weight: 700; font-size: 0.88rem; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer;" onclick="reapplyPoll()">
                    🔄 माहिती दुरुस्त करून पुन्हा अर्ज करा (Failed - Reapply Application)
                  </button>
                </div>
              `;
            }
          }
        }
      });
    } catch (e) {
      console.warn('Socket connect notice:', e);
    }
  };

  if (window.io) {
    setupConnection();
  } else {
    const s = document.createElement('script');
    s.src = `${portalOrigin}/socket.io/socket.io.js`;
    s.onload = setupConnection;
    document.head.appendChild(s);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initPollSocket();
  if (handoff.appId || handoff.pan || handoff.applicant) {
    startSamanvayHandoff();
  } else {
    switchTab('apply');
  }
});

window.addEventListener('DOMContentLoaded', () => {
  ['topSamanvayBtn', 'navSamanvayBtn', 'footerSamanvayBtn'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.onclick = (e) => {
        e.preventDefault();
        returnToSamanvay();
      };
    }
  });
});
