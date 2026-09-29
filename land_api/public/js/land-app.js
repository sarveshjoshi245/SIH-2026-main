/**
 * MAHARASHTRA BHUMI ABHILEKH (MAHABHULEKH / महाभूमी)
 * Client-side Controller & Dynamic Renderer
 */

let currentDivision = 'pune';
let divisionsData = [];
let currentTab = '7-12';
let currentLanguage = 'mr'; // 'mr' (मराठी) or 'en' (English)

// ── Samanvay hand-off ───────────────────────────────────────────────────────────
// The Samanvay dashboard opens this portal with ?app_id=…&callback=…&survey=…&pan=…
// &applicant=…&email=…&mobile=… . We pre-fill the application, and after it is
// submitted we send the citizen back with land_status=COMPLETED so Samanvay
// unlocks the next step (Electricity).
const handoff = (() => {
  const p = new URLSearchParams(window.location.search);
  return {
    appId: p.get('app_id'),
    callback: p.get('callback'),
    survey: p.get('survey') || '',
    pan: (p.get('pan') || '').toUpperCase(),
    applicant: p.get('applicant') || '',
  };
})();
// Where Samanvay is: the exact address that opened us (callback) if there is one;
// otherwise this page's own hostname + the portal port published from ports.json.
// Never a hard-coded port.
const SAMANVAY_ORIGIN = (() => {
  try { if (handoff.callback) return new URL(handoff.callback).origin; } catch (e) { /* bad callback */ }
  const port = window.SAMANVAY_PORTAL_PORT || 5001;
  return `${window.location.protocol}//${window.location.hostname}:${port}`;
})();
let lastApplicationRef = '';

let landSocket = null;

function initLandSocket() {
  const portalOrigin = SAMANVAY_ORIGIN || 'http://127.0.0.1:5001';
  const setupConnection = () => {
    if (landSocket || !window.io) return;
    try {
      landSocket = io(portalOrigin);
      landSocket.on('applicationUpdated', (data) => {
        if (!data) return;
        const currentPan = handoff.pan || (document.getElementById('applyPan')?.value || '').toUpperCase();
        if (data.department === 'LAND' && (data.citizenPan === currentPan || data.refNo === lastApplicationRef)) {
          const msgEl = document.getElementById('applyMsg');
          if (data.status === 'APPROVED') {
            if (landAdminPollTimer) clearInterval(landAdminPollTimer);
            renderLandApprovedDetails(data.application || data, msgEl);
          } else if (data.status === 'REJECTED') {
            if (landAdminPollTimer) clearInterval(landAdminPollTimer);
            if (msgEl) {
              msgEl.innerHTML = `
                <div style="background: #fef2f2; border: 2px solid #ef4444; color: #991b1b; padding: 16px; border-radius: 8px; margin-top: 14px;">
                  <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
                    <span>❌</span> <span>अर्जाची स्थिती: अयशस्वी / नामंजूर (Status: FAILED / REJECTED)</span>
                  </div>
                  <div style="font-size: 0.88rem; margin-top: 6px;">कारण: <strong>${data.adminRemarks || 'माहिती जुळली नाही.'}</strong></div>
                  <div style="margin-top: 14px;">
                    <button type="button" class="mb-btn" style="background: #dc3545; color: white; font-weight: 700; font-size: 0.88rem; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer;" onclick="reapplyLand()">
                      🔄 माहिती दुरुस्त करून पुन्हा अर्ज करा (Failed - Reapply Application)
                    </button>
                  </div>
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

document.addEventListener('DOMContentLoaded', async () => {
  await loadDivisions();
  initLandSocket();
  if (handoff.appId) {
    startSamanvayHandoff();
  } else {
    switchTab('apply');
    presetLookup('101', 'Pune', 'Haveli', 'Wagholi');
  }
});

function startSamanvayHandoff() {
  switchTab('apply');
  const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
  setVal('applySurvey', handoff.survey);
  setVal('applyPan', handoff.pan);
  setVal('applyName', handoff.applicant);
  const banner = document.getElementById('samanvayHandoff');
  if (banner) banner.hidden = false;
  if (handoff.pan) {
    fillProfileFromSamanvay(handoff.pan);
    checkExistingLandAdminStatus(handoff.pan);
  }
}

async function checkExistingLandAdminStatus(pan) {
  const portalOrigin = SAMANVAY_ORIGIN || 'http://127.0.0.1:5001';
  const msgEl = document.getElementById('applyMsg');
  try {
    const res = await fetch(`${portalOrigin}/api/admin/my-applications?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();
    if (data.success && data.applications) {
      const app = data.applications.find(a => a.department === 'LAND');
      if (app) {
        if (app.status === 'APPROVED') {
          renderLandApprovedDetails(app, msgEl);
        } else if (app.status === 'PENDING') {
          renderLandStatusPending(msgEl, app.ref_no, app.ref_number || handoff.survey || '101');
          if (landAdminPollTimer) clearInterval(landAdminPollTimer);
          landAdminPollTimer = setInterval(() => pollLandAdminStatus(pan, app.ref_no, msgEl), 3000);
        }
      }
    }
  } catch (e) {}
}

// Same lookup the previous portal used: the citizen's verified profile in Samanvay's database.
async function fillProfileFromSamanvay(pan) {
  const msg = document.getElementById('samanvayProfileMsg');
  if (!SAMANVAY_ORIGIN) { if (msg) msg.textContent = '⚠️ समन्वयचा पत्ता मिळाला नाही — कृपया माहिती स्वतः भरा. (Samanvay address missing — please fill in manually.)'; return; }
  if (msg) msg.textContent = '🔄 समन्वय मधून प्रोफाइल आणत आहे… (Fetching your profile from Samanvay…)';
  try {
    const res = await fetch(`${SAMANVAY_ORIGIN}/api/portal/user-profile?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();
    if (data.success && data.found && data.profile) {
      const p = data.profile;
      const nameEl = document.getElementById('applyName');
      if (nameEl) nameEl.value = p.organization_name || p.full_name || nameEl.value;
      const panEl = document.getElementById('applyPan');
      if (panEl && p.pan) panEl.value = p.pan;
      if (p.district) { const el = document.getElementById('applyDistrict'); if (el) el.value = p.district; }
      if (p.taluka) { const el = document.getElementById('applyTaluka'); if (el) el.value = p.taluka; }
      if (p.village) { const el = document.getElementById('applyVillage'); if (el) el.value = p.village; }
      if (msg) msg.textContent = `✅ माहिती आपोआप भरली: ${p.organization_name || p.full_name} (Profile auto-filled — ready to submit)`;
    } else if (msg) {
      msg.textContent = '⚠️ या पॅनसाठी प्रोफाइल सापडले नाही — कृपया माहिती स्वतः भरा. (No profile found for this PAN — please fill in manually.)';
    }
  } catch (err) {
    if (msg) msg.textContent = '⚠️ समन्वयशी जोडणी झाली नाही — कृपया माहिती स्वतः भरा. (Could not reach Samanvay — please fill in manually.)';
  }
}

function returnToSamanvay() {
  const ref = lastApplicationRef || ('LND-' + Date.now().toString().slice(-8));
  const url = `${SAMANVAY_ORIGIN}/dashboard.html?tab=flowchart&app_id=${encodeURIComponent(handoff.appId || '')}&land_status=COMPLETED&land_ref=${encodeURIComponent(ref)}`;
  window.location.href = url;
}

// ── Language Toggle ─────────────────────────────────────────────────────────────
function setLanguage(lang) {
  currentLanguage = lang;
  document.querySelectorAll('.lang-mr').forEach(el => el.style.display = lang === 'mr' ? '' : 'none');
  document.querySelectorAll('.lang-en').forEach(el => el.style.display = lang === 'en' ? '' : 'none');
  populateDistricts(currentDivision);
}

// ── Load Divisions ──────────────────────────────────────────────────────────────
async function loadDivisions() {
  try {
    const res = await fetch('/api/land/mahabhulekh/divisions');
    const data = await res.json();
    divisionsData = data.divisions || [];
    renderDivisionsGrid();
    populateDistricts('pune');
  } catch (err) {
    console.error('Failed to load divisions:', err);
  }
}

function renderDivisionsGrid() {
  const container = document.getElementById('divisionGrid');
  if (!container) return;

  container.innerHTML = divisionsData.map(d => `
    <div class="mb-division-card ${d.id === currentDivision ? 'selected' : ''}" onclick="selectDivision('${d.id}')">
      <div class="mb-division-name">${d.name_mr}</div>
      <div class="mb-division-sub">${d.name_en} (${d.districts.length} जिल्हे)</div>
    </div>
  `).join('');
}

function selectDivision(divId) {
  currentDivision = divId;
  renderDivisionsGrid();
  populateDistricts(divId);
}

function populateDistricts(divId) {
  const divObj = divisionsData.find(d => d.id === divId) || divisionsData[0];
  const districtSelect = document.getElementById('selDistrict');
  if (!districtSelect || !divObj) return;

  districtSelect.innerHTML = divObj.districts.map(dist => 
    `<option value="${dist.id}" data-name-en="${dist.name_en}" data-name-mr="${dist.name_mr}">${dist.name_mr} (${dist.name_en})</option>`
  ).join('');

  onDistrictChange();
}

function onDistrictChange() {
  const divObj = divisionsData.find(d => d.id === currentDivision) || divisionsData[0];
  const districtSelect = document.getElementById('selDistrict');
  const talukaSelect = document.getElementById('selTaluka');
  if (!districtSelect || !talukaSelect || !divObj) return;

  const selectedDistId = districtSelect.value;
  const distObj = divObj.districts.find(d => d.id === selectedDistId) || divObj.districts[0];

  talukaSelect.innerHTML = distObj ? distObj.talukas.map(t => 
    `<option value="${t.id}" data-name-en="${t.name_en}" data-name-mr="${t.name_mr}">${t.name_mr} (${t.name_en})</option>`
  ).join('') : '';

  onTalukaChange();
}

function onTalukaChange() {
  const divObj = divisionsData.find(d => d.id === currentDivision) || divisionsData[0];
  const districtSelect = document.getElementById('selDistrict');
  const talukaSelect = document.getElementById('selTaluka');
  const villageSelect = document.getElementById('selVillage');
  if (!districtSelect || !talukaSelect || !villageSelect || !divObj) return;

  const distObj = divObj.districts.find(d => d.id === districtSelect.value);
  const talukaObj = distObj ? distObj.talukas.find(t => t.id === talukaSelect.value) : null;

  villageSelect.innerHTML = talukaObj ? talukaObj.villages.map(v => 
    `<option value="${v.id}" data-name-en="${v.name_en}" data-name-mr="${v.name_mr}">${v.name_mr} (${v.name_en})</option>`
  ).join('') : '';
}

// ── Tab Switching ───────────────────────────────────────────────────────────────
function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.mb-nav a').forEach(a => a.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) activeNav.classList.add('active');

  const tabContainers = ['7-12', '8-a', 'ferfar', 'aapli-chawadi', 'apply', 'all-records'];
  tabContainers.forEach(t => {
    const el = document.getElementById(`section-${t}`);
    if (el) el.style.display = t === tabId ? 'block' : 'none';
  });

  if (tabId === 'all-records') {
    fetchAllRecords();
  } else if (tabId === 'ferfar') {
    fetchFerfarRecords();
  } else if (tabId === 'aapli-chawadi') {
    fetchAapliChawadi();
  }
}

// ── Preset Quick Lookup ─────────────────────────────────────────────────────────
function presetLookup(surveyNo, district, taluka, village) {
  const searchInput = document.getElementById('searchQuery');
  if (searchInput) searchInput.value = surveyNo;

  const radioSurvey = document.getElementById('radioSurvey');
  if (radioSurvey) radioSurvey.checked = true;

  handleSearch712();
}

// ── Fetch & Render 7/12 Extract ─────────────────────────────────────────────────
async function handleSearch712(e) {
  if (e) e.preventDefault();
  const searchBtn = document.getElementById('btnSearch712');
  const resultContainer = document.getElementById('result712');
  const query = (document.getElementById('searchQuery')?.value || '101').trim();

  let searchType = 'survey';
  if (document.getElementById('radioKhata')?.checked) searchType = 'khata';
  if (document.getElementById('radioName')?.checked) searchType = 'name';
  if (document.getElementById('radioPan')?.checked) searchType = 'pan';

  const distSelect = document.getElementById('selDistrict');
  const talSelect = document.getElementById('selTaluka');
  const vilSelect = document.getElementById('selVillage');

  const district = distSelect?.options[distSelect.selectedIndex]?.dataset.nameEn || '';
  const taluka = talSelect?.options[talSelect.selectedIndex]?.dataset.nameEn || '';
  const village = vilSelect?.options[vilSelect.selectedIndex]?.dataset.nameEn || '';

  if (searchBtn) searchBtn.disabled = true;
  if (resultContainer) {
    resultContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: var(--mb-maroon);">
        <div style="font-size: 1.5rem; margin-bottom: 8px;">⏳</div>
        <strong>महाराष्ट्र भूमी अभिलेख प्रणालीतून ७/१२ उतारा प्राप्त करत आहे...</strong>
      </div>
    `;
  }

  try {
    const url = `/api/land/mahabhulekh/7-12?query=${encodeURIComponent(query)}&searchType=${searchType}&district=${encodeURIComponent(district)}&taluka=${encodeURIComponent(taluka)}&village=${encodeURIComponent(village)}`;
    const res = await fetch(url);
    const data = await res.json();

    if (!res.ok || !data.success) {
      resultContainer.innerHTML = `
        <div class="mb-card" style="border-left: 4px solid #dc3545; padding: 20px;">
          <h4 style="color: #dc3545; margin-bottom: 6px;">रेकॉर्ड आढळले नाही (No Record Found)</h4>
          <p style="color: var(--mb-text-muted); font-size: 0.9rem;">${data.message || 'या निकषांवर कोणताही सातबारा उतारा उपलब्ध नाही.'}</p>
        </div>
      `;
      return;
    }

    renderSatbara712(data.record, data.uin);
  } catch (err) {
    resultContainer.innerHTML = `
      <div class="mb-card" style="border-left: 4px solid #dc3545; padding: 20px;">
        <h4 style="color: #dc3545;">API त्रुटी (Connection Error)</h4>
        <p style="color: var(--mb-text-muted);">${err.message}</p>
      </div>
    `;
  } finally {
    if (searchBtn) searchBtn.disabled = false;
  }
}

function renderSatbara712(r, uin) {
  const container = document.getElementById('result712');
  if (!container) return;

  const isApproved = r.jamabandi === 'APPROVED';
  const isPending = r.jamabandi === 'PENDING';
  const isRejected = r.jamabandi === 'REJECTED';

  const statusBadge = isApproved 
    ? `<span style="background: #198754; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">प्रमाणित / APPROVED</span>`
    : isPending
    ? `<span style="background: #ffc107; color: #000; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">प्रलंबित फेरफार / PENDING MUTATION</span>`
    : `<span style="background: #dc3545; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">नामंजूर / REJECTED</span>`;

  const cropsHtml = (r.crop_data && r.crop_data.length > 0) ? r.crop_data.map(c => `
    <tr>
      <td style="text-align: center;">${c.year || '2025-26'}</td>
      <td style="text-align: center;">${c.season || 'वार्षिक'}</td>
      <td><strong>${c.crop_name || 'अकृषिक'}</strong></td>
      <td style="text-align: right;">${c.area || r.kshetra} हे.आर</td>
      <td style="text-align: center;">${c.irrigation_source || 'एमआयडीसी / विहीर'}</td>
      <td style="text-align: center;">${c.mixed_crop || 'नाही'}</td>
    </tr>
  `).join('') : `
    <tr>
      <td colspan="6" style="text-align: center; color: #666;">पिकांची नोंद उपलब्ध नाही / अकृषिक जमीन</td>
    </tr>
  `;

  container.innerHTML = `
    <!-- Top Action Bar -->
    <div class="no-print" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; color: var(--mb-maroon);">
        📄 सातबारा उतारा (गाव नमुना ७ व १२) • UIN: <span style="font-family: monospace; color: #000;">${uin || 'MH-PUN-101'}</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="mb-btn mb-btn-outline" onclick="window.print()" style="padding: 6px 14px; font-size: 0.85rem;">
          🖨️ मुद्रण (Print / Save PDF)
        </button>
        <button class="mb-btn mb-btn-primary" onclick="simulateMutationToggle('${r.gtn}')" style="padding: 6px 14px; font-size: 0.85rem;">
          ⚙️ फेरफार स्थिती बदला (Simulate Mutation)
        </button>
      </div>
    </div>

    <!-- Official 7/12 Sheet -->
    <div class="satbara-sheet">
      <div class="satbara-watermark">महाराष्ट्र शासन • महसूल विभाग</div>

      <div class="satbara-header">
        <h2>महाराष्ट्र शासन • महसूल विभाग (GOVERNMENT OF MAHARASHTRA)</h2>
        <h3>गाव नमुना सात (अधिकार अभिलेख पत्रक) व गाव नमुना बारा (पिकांची पाहणी नोंदवही)</h3>
        <p style="font-size: 0.8rem; color: #444; margin-top: 2px;">(महाराष्ट्र जमीन महसूल अधिकार अभिलेख आणि नोंदवह्या तयार करणे व सुस्थितीत ठेवणे नियम १९७१ यातील नियम ३, ५, ६ आणि २९)</p>
      </div>

      <div class="satbara-meta">
        <div><strong>गाव:</strong> ${r.village_mr || r.village} (${r.village})</div>
        <div><strong>तालुका:</strong> ${r.taluka_mr || r.taluka} (${r.taluka})</div>
        <div><strong>जिल्हा:</strong> ${r.district_mr || r.district} (${r.district})</div>
        <div><strong>गट / सर्व्हे क्र.:</strong> <span style="font-size: 1.1rem; color: #780000;">${r.gtn || r.survey_number}</span></div>
      </div>

      <!-- FORM 7 SECTION -->
      <table class="satbara-table">
        <thead>
          <tr>
            <th style="width: 25%;">भूमापन क्रमांक व उपविभाग</th>
            <th style="width: 25%;">भोगवटादाराचे नाव व हिस्सा</th>
            <th style="width: 25%;">क्षेत्र व आकारणी</th>
            <th style="width: 25%;">इतर हक्क व फेरफार</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div style="font-weight: 700; font-size: 1rem; color: #780000;">गट क्र. ${r.gtn}</div>
              <div style="margin-top: 4px; font-size: 0.82rem; color: #555;">उपविभाग / हिस्सा: <strong>${r.hissa_no || '१'}</strong></div>
              <div style="margin-top: 4px; font-size: 0.82rem;"><strong>खाते क्रमांक:</strong> <span style="background: #eee; padding: 1px 6px; border-radius: 3px;">${r.khata_no || '४५२'}</span></div>
              <div style="margin-top: 8px; font-size: 0.82rem;"><strong>धारणा प्रकार / वर्ग:</strong><br>${r.bhogvatadar_varg || 'भोगवटादार वर्ग - १'}</div>
            </td>
            <td>
              <div style="font-weight: 700; font-size: 0.95rem; line-height: 1.3;">
                ${r.malak_name || 'मे. एबीसी इंडस्ट्रीज प्रा. लि.'}
              </div>
              <div style="font-size: 0.8rem; color: #555; margin-top: 4px;">
                PAN: <strong style="letter-spacing: 0.5px;">${r.malak_pan || 'ABCDE1234F'}</strong>
              </div>
              <div style="font-size: 0.8rem; color: #555;">
                आधार: <strong>${r.malak_aadhaar ? 'XXXX-XXXX-' + r.malak_aadhaar.slice(-4) : 'XXXX-XXXX-5544'}</strong>
              </div>
              <div style="margin-top: 8px; font-size: 0.82rem;">
                <strong>जमीन वापर:</strong> ${r.jamin_prakar_mr || r.jamin_prakar || 'अकृषिक - औद्योगिक'}
              </div>
              <div style="margin-top: 6px;">
                ${statusBadge}
              </div>
            </td>
            <td>
              <div style="display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding-bottom: 3px;">
                <span>लागवडीयोग्य क्षेत्र:</span>
                <strong>${(parseFloat(r.kshetra) - parseFloat(r.pot_kharaba || 0)).toFixed(2)} हे.आर</strong>
              </div>
              <div style="display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 3px 0;">
                <span>पोटखराबा क्षेत्र:</span>
                <strong>${r.pot_kharaba || '०.१०'} हे.आर</strong>
              </div>
              <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding: 4px 0; font-weight: 700;">
                <span>एकूण क्षेत्र:</span>
                <span style="color: #780000;">${r.kshetra} ${r.kshetra_unit || 'हेक्टर'}</span>
              </div>
              <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.82rem;">
                <span>आकारणी (रुपये):</span>
                <strong>रु. ${r.aakarni || '४५.५०'}</strong>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.82rem;">
                <span>जुडी / विशेष कर:</span>
                <strong>रु. ${r.judi_tax || '०.००'}</strong>
              </div>
            </td>
            <td>
              <div style="font-size: 0.82rem; margin-bottom: 6px;">
                <strong>प्रमाणित फेरफार नोंदी:</strong><br>
                ${(r.ferfar_nos || ['१०४५', '११८२', '१२९०']).map(f => `<span style="display: inline-block; background: #e8f4ec; color: #1a5632; padding: 1px 6px; margin: 2px; border-radius: 3px; font-weight: 600;">क्र. ${f}</span>`).join(' ')}
              </div>
              <div style="font-size: 0.82rem; margin-top: 6px; color: ${r.pending_ferfar && r.pending_ferfar !== 'निरंक' ? '#b45309' : '#555'};">
                <strong>प्रलंबित फेरफार:</strong> ${r.pending_ferfar || 'निरंक'}
              </div>
              <div style="font-size: 0.82rem; margin-top: 6px; color: ${r.bandhak ? '#dc2626' : '#15803d'};">
                <strong>बोजा / कर्ज:</strong> ${r.boja_details || (r.bandhak ? 'कर्ज बोजा लागू' : 'निरंक (बोजा नाही)')}
              </div>
              <div style="font-size: 0.82rem; margin-top: 4px; color: ${r.court_case ? '#dc2626' : '#555'};">
                <strong>न्यायालयीन वाद:</strong> ${r.court_details || (r.court_case ? 'वादग्रस्त' : 'निरंक')}
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- FORM 12 SECTION -->
      <div style="font-weight: 700; font-size: 0.95rem; margin: 14px 0 6px 0; color: #222; border-bottom: 1px solid #333; padding-bottom: 4px;">
        गाव नमुना बारा (पिकांची पाहणी नोंदवही - Crop Inspection Sheet)
      </div>

      <table class="satbara-table">
        <thead>
          <tr>
            <th>वर्ष</th>
            <th>हंगाम</th>
            <th>पिकाचे नाव व जात</th>
            <th>जलसिंचित / लागवड क्षेत्र</th>
            <th>पाण्याचा स्त्रोत</th>
            <th>मिश्र पीक</th>
          </tr>
        </thead>
        <tbody>
          ${cropsHtml}
        </tbody>
      </table>

      <!-- Digital Signature Stamp & QR Code -->
      <div class="satbara-digital-sign">
        <div>
          <div class="satbara-seal-box">
            🛡️ <strong>डिजिटल स्वाक्षरीत अधिकृत उतारा (Digitally Signed Record)</strong><br>
            तलाठी / मंडळ अधिकारी: <strong>${r.talathi_name || 'तलाठी कार्यालय'}</strong><br>
            स्वाक्षरी दिनांक व वेळ: <strong>${new Date().toLocaleString('mr-IN')}</strong>
          </div>
        </div>
        <div style="text-align: right; display: flex; align-items: center; gap: 12px;">
          <div style="font-size: 0.75rem; color: #555;">
            सदर ७/१२ उतारा हा <strong>महाभूमी / महाभूलेख</strong> प्रणालीद्वारे<br>
            डिजिटल स्वाक्षरीत असून शासकीय कामकाजासाठी वैध आहे.
          </div>
          <div style="background: #f8f9fa; border: 1px solid #333; padding: 6px; font-family: monospace; font-size: 0.7rem; text-align: center;">
            <div style="font-size: 1.8rem; line-height: 1;">📱</div>
            QR VERIFIED
          </div>
        </div>
      </div>
    </div>
  `;
}

// ── Fetch & Render 8-A Extract ──────────────────────────────────────────────────
async function handleSearch8A(e) {
  if (e) e.preventDefault();
  const query = (document.getElementById('search8AQuery')?.value || '452').trim();
  const container = document.getElementById('result8A');

  container.innerHTML = `
    <div style="text-align: center; padding: 24px; color: var(--mb-maroon);">
      ⏳ गाव नमुना ८-अ खाते उतारा शोधत आहे...
    </div>
  `;

  try {
    const res = await fetch(`/api/land/mahabhulekh/8-a?query=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (!res.ok || !data.success) {
      container.innerHTML = `<div class="mb-card" style="padding: 20px; color: #dc3545;">${data.message || '८-अ खाते उतारा आढळला नाही.'}</div>`;
      return;
    }

    const ext = data.extract;
    container.innerHTML = `
      <div class="satbara-sheet">
        <div class="satbara-header">
          <h2>महाराष्ट्र शासन • महसूल विभाग (GOVERNMENT OF MAHARASHTRA)</h2>
          <h3>गाव नमुना आठ-अ (८-अ खातेदाराच्या जमिनीची नोंदवही / Holding Register)</h3>
        </div>

        <div class="satbara-meta">
          <div><strong>खाते क्रमांक:</strong> <span style="color: #780000; font-size: 1.1rem;">${ext.khata_no}</span></div>
          <div><strong>खातेदाराचे नाव:</strong> <strong>${ext.malak_name}</strong></div>
          <div><strong>गाव:</strong> ${ext.village} | <strong>तालुका:</strong> ${ext.taluka} | <strong>जिल्हा:</strong> ${ext.district}</div>
        </div>

        <table class="satbara-table">
          <thead>
            <tr>
              <th>अनु. क्र.</th>
              <th>सर्व्हे / गट क्रमांक</th>
              <th>हिस्सा</th>
              <th>जमिनीचा प्रकार</th>
              <th>एकूण क्षेत्र (हे.आर)</th>
              <th>पोटखराबा</th>
              <th>आकारणी (रु.)</th>
              <th>फेरफार स्थिती</th>
            </tr>
          </thead>
          <tbody>
            ${ext.holdings.map((h, idx) => `
              <tr>
                <td style="text-align: center;">${idx + 1}</td>
                <td style="text-align: center; font-weight: 700; color: #780000;">गट क्र. ${h.survey_number}</td>
                <td style="text-align: center;">${h.hissa_no}</td>
                <td>${h.jamin_prakar}</td>
                <td style="text-align: right; font-weight: 600;">${h.area_hectares} हे.आर</td>
                <td style="text-align: right;">${h.pot_kharaba}</td>
                <td style="text-align: right;">रु. ${h.aakarni}</td>
                <td style="text-align: center;">
                  <span style="background: ${h.mutation_status === 'APPROVED' ? '#198754' : '#ffc107'}; color: ${h.mutation_status === 'APPROVED' ? '#fff' : '#000'}; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;">
                    ${h.mutation_status}
                  </span>
                </td>
              </tr>
            `).join('')}
            <tr style="background: #f8f9fa; font-weight: 700;">
              <td colspan="4" style="text-align: right;">एकूण खाते धारणा (Total Holding):</td>
              <td style="text-align: right; color: #780000;">${ext.total_area_hectares} हेक्टर</td>
              <td style="text-align: right;">${ext.total_pot_kharaba}</td>
              <td style="text-align: right;">रु. ${ext.total_aakarni}</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="mb-card" style="padding: 20px; color: #dc3545;">त्रुटी: ${err.message}</div>`;
  }
}

// ── Fetch e-Ferfar ──────────────────────────────────────────────────────────────
async function fetchFerfarRecords() {
  const container = document.getElementById('resultFerfar');
  if (!container) return;

  try {
    const res = await fetch('/api/land/mahabhulekh/ferfar');
    const data = await res.json();
    const list = data.ferfar_records || [];

    container.innerHTML = `
      <table class="satbara-table">
        <thead>
          <tr>
            <th>फेरफार क्र.</th>
            <th>गट / सर्व्हे क्र.</th>
            <th>गाव / तालुका</th>
            <th>फेरफार प्रकार / नोंदीचे स्वरूप</th>
            <th>अर्जदार / खरेदीदार</th>
            <th>माजी मालक</th>
            <th>अर्ज दिनांक</th>
            <th>स्थिती (Status)</th>
          </tr>
        </thead>
        <tbody>
          ${list.map(f => `
            <tr>
              <td style="text-align: center; font-weight: 800; color: #780000;">क्र. ${f.ferfar_no}</td>
              <td style="text-align: center; font-weight: 700;">गट ${f.survey_number}</td>
              <td>${f.village}, ${f.taluka}</td>
              <td><strong>${f.mutation_type}</strong></td>
              <td>${f.applicant_name}</td>
              <td>${f.previous_owner}</td>
              <td style="text-align: center;">${f.application_date}</td>
              <td style="text-align: center;">
                <span style="background: ${f.status === 'CERTIFIED' ? '#198754' : '#ffc107'}; color: ${f.status === 'CERTIFIED' ? '#fff' : '#000'}; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">
                  ${f.status_mr || f.status}
                </span>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    container.innerHTML = `<p style="color: #dc3545;">त्रुटी: ${err.message}</p>`;
  }
}

// ── Fetch Aapli Chawadi ─────────────────────────────────────────────────────────
async function fetchAapliChawadi() {
  const container = document.getElementById('resultAapliChawadi');
  if (!container) return;

  try {
    const res = await fetch('/api/land/mahabhulekh/aapli-chawadi');
    const data = await res.json();
    const notices = data.notices || [];

    container.innerHTML = `
      <div style="margin-bottom: 16px; font-size: 0.9rem; color: #555;">
        महाराष्ट्र जमीन महसूल संहिता १९६६ कलम १३५-ड अन्वये गावनिहाय जाहीर नोटीस फलक.
      </div>
      <div style="display: grid; gap: 14px;">
        ${notices.map(n => `
          <div class="mb-card" style="border-left: 4px solid var(--mb-maroon); margin-bottom: 0;">
            <div class="mb-card-header" style="background: #fff8f5;">
              <span>📜 नोटीस क्र. ${n.notice_no || '135D'} • फेरफार क्र. ${n.ferfar_no || '1402'} (गट क्र. ${n.survey_number || '103'})</span>
              <span style="font-size: 0.8rem; color: #780000;">मुदत: ${n.expiry_date || '15 दिवस'}</span>
            </div>
            <div class="mb-card-body" style="font-size: 0.92rem; line-height: 1.5;">
              <p>${n.details || 'अधिकार अभिलेखात बदल करण्याबाबत जाहीर नोटीस.'}</p>
              <div style="margin-top: 10px; font-size: 0.8rem; color: #666;">
                गाव: <strong>${n.village || 'वाघोली'}</strong> | तालुका: <strong>${n.taluka || 'हवेली'}</strong> | प्रसिद्ध दिनांक: <strong>${n.notice_date || '2026-02-20'}</strong>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p style="color: #dc3545;">त्रुटी: ${err.message}</p>`;
  }
}

// ── Fetch All Records (Admin / Audit) ───────────────────────────────────────────
async function fetchAllRecords() {
  const container = document.getElementById('resultAllRecords');
  if (!container) return;

  try {
    const res = await fetch('/api/land/all');
    const data = await res.json();
    const records = data.records || [];

    container.innerHTML = `
      <div style="margin-bottom: 12px; font-weight: 700; color: var(--mb-maroon);">
        एकूण रेकॉर्ड्स (Total Records in MahaBhulekh Database): ${records.length}
      </div>
      <table class="satbara-table">
        <thead>
          <tr>
            <th>गट क्र.</th>
            <th>खातेदार / मालक</th>
            <th>PAN</th>
            <th>गाव / तालुका</th>
            <th>क्षेत्र</th>
            <th>वापर</th>
            <th>जमाबंदी / फेरफार</th>
            <th>बोजा</th>
            <th>न्यायालय</th>
          </tr>
        </thead>
        <tbody>
          ${records.map(r => `
            <tr>
              <td style="text-align: center; font-weight: 800; color: #780000;">${r.gtn}</td>
              <td><strong>${r.malak_name}</strong></td>
              <td style="font-family: monospace;">${r.malak_pan}</td>
              <td>${r.village}, ${r.taluka}</td>
              <td style="text-align: right;">${r.kshetra} HA</td>
              <td>${r.jamin_prakar}</td>
              <td style="text-align: center;">
                <span style="background: ${r.jamabandi === 'APPROVED' ? '#198754' : (r.jamabandi === 'PENDING' ? '#ffc107' : '#dc3545')}; color: ${r.jamabandi === 'PENDING' ? '#000' : '#fff'}; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700;">
                  ${r.jamabandi}
                </span>
              </td>
              <td style="text-align: center; color: ${r.bandhak ? '#dc2626' : '#15803d'}; font-weight: 700;">${r.bandhak ? 'होय' : 'नाही'}</td>
              <td style="text-align: center; color: ${r.court_case ? '#dc2626' : '#15803d'}; font-weight: 700;">${r.court_case ? 'होय' : 'नाही'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    container.innerHTML = `<p style="color: #dc3545;">त्रुटी: ${err.message}</p>`;
  }
}

// ── Apply for Mutation / Land Certificate ───────────────────────────────────────
let landAdminPollTimer = null;

async function handleApplySubmit(e) {
  e.preventDefault();
  const surveyNumber = document.getElementById('applySurvey').value.trim();
  const pan = document.getElementById('applyPan').value.trim().toUpperCase();
  const applicantName = document.getElementById('applyName').value.trim();
  const area = document.getElementById('applyArea').value.trim();
  const district = document.getElementById('applyDistrict').value.trim();
  const taluka = document.getElementById('applyTaluka').value.trim();
  const village = document.getElementById('applyVillage').value.trim();
  const msgEl = document.getElementById('applyMsg');

  const back = document.getElementById('returnToSamanvay');
  if (back) back.hidden = true; // Hide Go Back button initially!

  if (msgEl) {
    msgEl.innerHTML = `<div style="padding: 12px; color: var(--mb-maroon);">⏳ अर्ज महसूल प्रणालीमध्ये दाखल करत आहे...</div>`;
  }

  let adminRefNo = '';
  const portalOrigin = SAMANVAY_ORIGIN || 'http://127.0.0.1:5001';

  try {
    const adminRes = await fetch(`${portalOrigin}/api/admin/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        department: 'LAND',
        citizenName: applicantName,
        citizenPan: pan,
        projectName: `Land 7/12 Survey #${surveyNumber}`,
        projectType: 'LAND_REVENUE',
        district: district || 'Pune',
        refNumber: surveyNumber
      })
    });
    const adminData = await adminRes.json();
    if (adminData.success) adminRefNo = adminData.refNo;
  } catch (err) {
    console.warn('Admin submit error:', err.message);
  }

  try {
    const res = await fetch('/api/land/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ surveyNumber, pan, applicantName, area, district, taluka, village })
    });
    const data = await res.json();
    lastApplicationRef = adminRefNo || data.application_ref || '';

    // Render Initial PENDING Box
    renderLandStatusPending(msgEl, lastApplicationRef, surveyNumber);

    // Poll Admin Panel status until APPROVED or REJECTED
    if (landAdminPollTimer) clearInterval(landAdminPollTimer);
    landAdminPollTimer = setInterval(() => pollLandAdminStatus(pan, lastApplicationRef, msgEl), 3000);
    pollLandAdminStatus(pan, lastApplicationRef, msgEl);

  } catch (err) {
    if (msgEl) {
      msgEl.innerHTML = `<div style="color: #dc3545; padding: 12px;">❌ नेटवर्क त्रुटी: ${err.message}</div>`;
    }
  }
}

function renderLandStatusPending(container, refNo, surveyNumber) {
  if (!container) return;
  container.innerHTML = `
    <div style="background: #fff8e1; border: 2px solid #f59e0b; color: #78350f; padding: 16px; border-radius: 8px; margin-top: 14px;">
      <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
        <span>⏳</span> <span>अर्जाची स्थिती: प्रलंबित (Status: PENDING)</span>
      </div>
      <div style="font-size: 0.88rem; margin-top: 6px;">अर्ज संदर्भ क्रमांक (Ref): <strong>${refNo}</strong> (गट क्र. ${surveyNumber})</div>
      <div style="font-size: 0.84rem; color: #92400e; margin-top: 6px;">
        तुमचा अर्ज विभाग प्रशासक <a href="http://127.0.0.1:5001/admin.html" target="_blank" style="color: #1e3a8a; font-weight: 700;">/admin.html</a> मध्ये छाननीखाली आहे. प्रशासकाकडून मंजुरी मिळाल्यावरच 'समन्वय पोर्टलवर परत जा' बटण उघडेल.
      </div>
    </div>
  `;
}

function renderLandApprovedDetails(app, container) {
  if (!container) return;
  const refNo = app.ref_no || app.refNumber || 'REF-LAND-001';
  const name = app.citizen_name || app.citizenName || 'Applicant Enterprise';
  const pan = app.citizen_pan || app.citizenPan || 'PAN0000000';
  const gatNo = app.ref_number || app.surveyNumber || '101';
  const dist = app.district || 'Pune';
  const remarks = app.admin_remarks || '✓ सातबारा व फेरफार दस्तऐवज तपासणी पूर्ण — अर्ज मंजूर.';

  lastApplicationRef = refNo;

  container.innerHTML = `
    <div style="background: #ffffff; border: 2px solid #166534; border-radius: 12px; padding: 22px; margin-top: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); font-family: system-ui, -apple-system, sans-serif;">
      
      <!-- Top Status Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
        <div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #166534; display: flex; align-items: center; gap: 8px;">
            <span>🏛️</span> <span>महसूल व वन विभाग (Land Records Department)</span>
          </div>
          <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">सातबारा व फेरफार अर्ज — अधिकृत मान्यता पत्र</div>
        </div>
        <span style="background: #dcfce7; color: #15803d; border: 1px solid #86efac; font-weight: 800; font-size: 0.85rem; padding: 6px 14px; border-radius: 9999px;">
          ✓ ACCEPTED & APPROVED
        </span>
      </div>

      <!-- Application Details Grid -->
      <div style="font-size: 0.88rem; margin-bottom: 12px; color: #1e293b; font-weight: 700;">अर्जाचे तपशील (Application Details):</div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 18px;">
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">अर्ज संदर्भ क्र. (Ref No)</div>
          <div style="font-weight: 800; font-size: 0.95rem; color: #0f172a; font-family: monospace;">${refNo}</div>
        </div>
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">अर्जदाराचे नाव (Applicant)</div>
          <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a;">${name}</div>
        </div>
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">पॅन क्रमांक (PAN)</div>
          <div style="font-weight: 800; font-size: 0.9rem; color: #0f172a; font-family: monospace;">${pan}</div>
        </div>
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">सर्व्हे / गट क्र. (Survey No)</div>
          <div style="font-weight: 800; font-size: 0.9rem; color: #0f172a;">Gat No. ${gatNo}</div>
        </div>
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">जिल्हा (District)</div>
          <div style="font-weight: 700; font-size: 0.9rem; color: #0f172a;">${dist}</div>
        </div>
        <div>
          <div style="font-size: 0.72rem; color: #64748b; font-weight: 700; text-transform: uppercase;">प्रशासकीय निर्णय (Decision)</div>
          <div style="font-weight: 800; font-size: 0.9rem; color: #166534;">APPROVED</div>
        </div>
      </div>

      <!-- Admin Remarks -->
      <div style="background: #f0fdf4; border-left: 4px solid #166534; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 6px 6px 0; font-size: 0.88rem; color: #166534;">
        💬 <strong>प्रशासकीय टीप (Admin Remark):</strong> ${remarks}
      </div>

      <!-- Visible Return to Samanvay Button directly below details -->
      <div style="text-align: center; margin-top: 10px;">
        <button type="button" class="mb-btn mb-btn-primary" onclick="returnToSamanvay()" style="background: #166534; color: #ffffff; font-size: 1.05rem; font-weight: 800; padding: 14px 28px; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 6px 20px rgba(22,101,52,0.3); display: inline-flex; align-items: center; gap: 10px; width: 100%; justify-content: center;">
          ↩ <span>समन्वय पोर्टलवर परत जा (Return to Samanvay Portal ➔)</span>
        </button>
      </div>

    </div>
  `;

  const back = document.getElementById('returnToSamanvay');
  if (back) back.hidden = false;
}

async function pollLandAdminStatus(pan, refNo, container) {
  if (!pan || !refNo) return;
  const portalOrigin = SAMANVAY_ORIGIN || 'http://127.0.0.1:5001';
  try {
    const res = await fetch(`${portalOrigin}/api/admin/my-applications?pan=${encodeURIComponent(pan)}`);
    const data = await res.json();
    if (!data.success || !data.applications) return;

    const app = data.applications.find(a => a.ref_no === refNo || a.department === 'LAND');
    if (!app) return;

    if (app.status === 'APPROVED') {
      if (landAdminPollTimer) clearInterval(landAdminPollTimer);
      renderLandApprovedDetails(app, container);
    } else if (app.status === 'REJECTED') {
      if (landAdminPollTimer) clearInterval(landAdminPollTimer);
      if (container) {
        container.innerHTML = `
          <div style="background: #fef2f2; border: 2px solid #ef4444; color: #991b1b; padding: 16px; border-radius: 8px; margin-top: 14px;">
            <div style="font-weight: 800; font-size: 1.05rem; display: flex; align-items: center; gap: 8px;">
              <span>❌</span> <span>अर्जाची स्थिती: अयशस्वी / नामंजूर (Status: FAILED / REJECTED)</span>
            </div>
            <div style="font-size: 0.88rem; margin-top: 6px;">कारण: <strong>${app.admin_remarks || 'माहिती जुळली नाही.'}</strong></div>
            <div style="margin-top: 14px;">
              <button type="button" class="mb-btn" style="background: #dc3545; color: white; font-weight: 700; font-size: 0.88rem; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer;" onclick="reapplyLand()">
                🔄 माहिती दुरुस्त करून पुन्हा अर्ज करा (Failed - Reapply Application)
              </button>
            </div>
          </div>
        `;
      }
      const back = document.getElementById('returnToSamanvay');
      if (back) back.hidden = true;
    }
  } catch (e) {}
}

function reapplyLand() {
  if (landAdminPollTimer) clearInterval(landAdminPollTimer);
  const msgEl = document.getElementById('applyMsg');
  if (msgEl) msgEl.innerHTML = '';
  document.getElementById('applySurvey').focus();
}

// ── Mutation Simulator Toggle ──────────────────────────────────────────────────
async function simulateMutationToggle(surveyNo) {
  const newStatus = prompt(`फेरफार स्थिती निवडा (Enter new status for Survey #${surveyNo}):\n1. APPROVED\n2. PENDING\n3. REJECTED\n4. UNDER_OBJECTION`, 'APPROVED');
  if (!newStatus) return;

  const valid = ['APPROVED', 'PENDING', 'REJECTED', 'UNDER_OBJECTION'];
  const formatted = newStatus.trim().toUpperCase();
  if (!valid.includes(formatted)) {
    alert(`अवैध स्थिती! कृपया यापैकी एक प्रविष्ट करा: ${valid.join(', ')}`);
    return;
  }

  try {
    const res = await fetch(`/api/land/records/${surveyNo}/mutation`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'land-admin-mutation-key-007'
      },
      body: JSON.stringify({ mutation_status: formatted })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ गट क्र. ${surveyNo} ची फेरफार स्थिती बदलून "${formatted}" करण्यात आली आहे!`);
      handleSearch712();
    } else {
      alert(`त्रुटी: ${data.message}`);
    }
  } catch (err) {
    alert(`नेटवर्क त्रुटी: ${err.message}`);
  }
}
