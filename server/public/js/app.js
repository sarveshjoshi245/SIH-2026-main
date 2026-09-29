// G2C & B2G Government Interoperability Gateway — Vanilla JavaScript Client Logic (Port 5000)

let currentSession = null;
let currentTxnData = null;
let isLandOutage = false;

document.addEventListener('DOMContentLoaded', () => {
  initFormListeners();
});

function initFormListeners() {
  const identifierInput = document.getElementById('identifierInput');
  const radioPan = document.getElementById('radioPan');
  const radioAadhaar = document.getElementById('radioAadhaar');
  const authForm = document.getElementById('authForm');

  if (radioPan && radioAadhaar) {
    radioPan.addEventListener('change', () => updateInputPlaceholder());
    radioAadhaar.addEventListener('change', () => updateInputPlaceholder());
  }

  if (identifierInput) {
    identifierInput.addEventListener('input', (e) => {
      const isAadhaar = document.getElementById('radioAadhaar').checked;
      let val = e.target.value;

      if (isAadhaar) {
        // Aadhaar 4-4-4 auto format
        const digits = val.replace(/\D/g, '').slice(0, 12);
        e.target.value = digits.replace(/(\d{4})(?=\d)/g, '$1-');
      } else {
        // PAN uppercase 10 chars
        e.target.value = val.replace(/[^a-zA-Z0-9]/g, '').slice(0, 10).toUpperCase();
      }
    });
  }

  if (authForm) {
    authForm.addEventListener('submit', handleRequestOtp);
  }
}

function updateInputPlaceholder() {
  const isAadhaar = document.getElementById('radioAadhaar').checked;
  const input = document.getElementById('identifierInput');
  const label = document.getElementById('identifierLabel');
  const tabPanLabel = document.getElementById('tabPanLabel');
  const tabAadhaarLabel = document.getElementById('tabAadhaarLabel');
  input.value = '';

  if (isAadhaar) {
    label.innerHTML = 'Enter 12-Digit Aadhaar <span class="req">*</span>';
    input.placeholder = '9988-7766-5544';
    tabAadhaarLabel.classList.add('active');
    tabPanLabel.classList.remove('active');
  } else {
    label.innerHTML = 'Enter 10-Character PAN <span class="req">*</span>';
    input.placeholder = 'ABCDE1234F';
    tabPanLabel.classList.add('active');
    tabAadhaarLabel.classList.remove('active');
  }
}

// Quick evaluator demo preset filler
function selectDemoPreset(type, value) {
  if (type === 'pan') {
    document.getElementById('radioPan').checked = true;
  } else {
    document.getElementById('radioAadhaar').checked = true;
  }
  updateInputPlaceholder();
  document.getElementById('identifierInput').value = value;
}

// Submit Request OTP
async function handleRequestOtp(e) {
  e.preventDefault();
  const isAadhaar = document.getElementById('radioAadhaar').checked;
  const rawVal = document.getElementById('identifierInput').value;
  const cleanVal = rawVal.replace(/[\s-]/g, '');

  const errorDiv = document.getElementById('authError');
  errorDiv.style.display = 'none';

  if (isAadhaar && cleanVal.length !== 12) {
    showError('Please enter a valid 12-digit Aadhaar number.');
    return;
  }
  if (!isAadhaar && cleanVal.length !== 10) {
    showError('Please enter a valid 10-character PAN number (e.g. ABCDE1234F).');
    return;
  }

  try {
    const res = await fetch('/api/auth/request-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        identifierType: isAadhaar ? 'aadhaar' : 'pan',
        identifierValue: cleanVal
      })
    });

    const data = await res.json();
    if (data.success) {
      currentTxnData = data;
      openOtpModal(data);
    } else {
      showError(data.message || 'Failed to request OTP');
    }
  } catch (err) {
    showError('Error connecting to backend auth server.');
  }
}

function showError(msg) {
  const errorDiv = document.getElementById('authError');
  errorDiv.innerText = msg;
  errorDiv.style.display = 'block';
}

// OTP Modal Handlers
function openOtpModal(txnData) {
  document.getElementById('otpModal').style.display = 'flex';
  document.getElementById('maskedPhoneSpan').innerText = txnData.maskedPhone;
  document.getElementById('demoOtpCodeSpan').innerText = txnData.demoOtpCode;
  document.getElementById('otpInput').value = '';
  document.getElementById('otpError').style.display = 'none';
}

function closeOtpModal() {
  document.getElementById('otpModal').style.display = 'none';
}

function autoFillOtp() {
  if (currentTxnData?.demoOtpCode) {
    document.getElementById('otpInput').value = currentTxnData.demoOtpCode;
  }
}

async function verifyOtpSubmit() {
  const otpVal = document.getElementById('otpInput').value.trim();
  const otpError = document.getElementById('otpError');
  otpError.style.display = 'none';

  if (otpVal.length < 6) {
    otpError.innerText = 'Please enter all 6 digits of the OTP code.';
    otpError.style.display = 'block';
    return;
  }

  try {
    const res = await fetch('/api/auth/verify-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        txnId: currentTxnData.txnId,
        otpCode: otpVal
      })
    });

    const data = await res.json();
    if (data.success) {
      currentSession = data.user;
      closeOtpModal();
      showDashboard(data.user);
    } else {
      otpError.innerText = data.message || 'Verification failed';
      otpError.style.display = 'block';
    }
  } catch (err) {
    otpError.innerText = 'Server error during verification.';
    otpError.style.display = 'block';
  }
}

// Render Dashboard View
function showDashboard(user) {
  document.getElementById('authSection').style.display = 'none';
  document.getElementById('dashboardSection').style.display = 'block';

  // Render User Card
  document.getElementById('userName').innerText = user.name;
  document.getElementById('userPan').innerText = user.pan ? `PAN: ${user.pan}` : `Aadhaar: ${user.aadhaar}`;
  document.getElementById('userSurvey').innerText = `Survey: #${user.registeredLandSurvey}`;

  evaluateProject(user.registeredLandSurvey);
  fetchAuditLogs();
}

async function evaluateProject(surveyNo) {
  const surveyToUse = surveyNo || currentSession?.registeredLandSurvey || '102';
  const outageAlert = document.getElementById('outageAlert');

  try {
    const res = await fetch('/api/interop/evaluate-project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        applicantPan: currentSession?.pan || 'ABCDE1234F',
        surveyNumber: surveyToUse
      })
    });

    const data = await res.json();
    if (res.status === 503) {
      outageAlert.style.display = 'block';
    } else if (data.success) {
      outageAlert.style.display = 'none';
      renderWorkflowList(data.workflow);
      document.getElementById('rawLegacyJson').innerText = JSON.stringify(data.rawLegacyPayload, null, 2);
      document.getElementById('canonicalJson').innerText = JSON.stringify(data.canonicalModel, null, 2);
    } else {
      outageAlert.style.display = 'block';
      outageAlert.innerText = data.message || 'Evaluation error';
    }
    fetchAuditLogs();
  } catch (err) {
    outageAlert.style.display = 'block';
    outageAlert.innerText = 'Server communication error';
  }
}

function renderWorkflowList(workflow) {
  const container = document.getElementById('workflowList');
  container.innerHTML = '';

  workflow.dependencies.forEach(dep => {
    let sc = { tag: 'tag-amber' };
    if (dep.status === 'RESOLVED') sc = { tag: 'tag-green' };
    if (dep.status === 'BLOCKED' || dep.status === 'FAILED') sc = { tag: 'tag-red' };

    const row = document.createElement('div');
    row.className = 'list-row';
    row.innerHTML = `
      <div style="flex: 1;">
        <span style="font-weight: 600; display: block;">${dep.title}</span>
        <span style="font-size: 11px; color: var(--text-muted);">${dep.department}</span>
      </div>
      <div style="flex: 1; text-align: right;">
        <span class="tag ${sc.tag}">${dep.status}</span>
        ${dep.reason ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${dep.reason}</div>` : ''}
      </div>
    `;
    container.appendChild(row);
  });
}

// Fetch live M2M audit logs
async function fetchAuditLogs() {
  try {
    const res = await fetch('/api/interop/audit-logs');
    const data = await res.json();
    if (data.success) {
      const list = document.getElementById('auditLogList');
      list.innerHTML = '';
      data.logs.slice(0, 5).forEach(log => {
        const item = document.createElement('div');
        item.className = 'audit-row';
        item.innerHTML = `
          <span>[${log.timestamp}] ${log.event || log.outcome} (Survey #${log.surveyNumber || 'N/A'})</span>
          <span style="color: var(--navy);">${log.id}</span>
        `;
        list.appendChild(item);
      });
    }
  } catch (err) {}
}

// Interactive Simulation Controls
async function toggleMutationStatus() {
  const surveyNo = currentSession.registeredLandSurvey;
  const currentPayloadText = document.getElementById('rawLegacyJson').innerText;
  let currentJamabandi = 'APPROVED';
  try {
    const parsed = JSON.parse(currentPayloadText);
    currentJamabandi = parsed.jamabandi;
  } catch (e) {}

  const newStatus = currentJamabandi === 'APPROVED' ? 'PENDING' : 'APPROVED';

  await fetch('/api/land/update-mutation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'GOV-INTEROP-SECRET-KEY'
    },
    body: JSON.stringify({ surveyNo, newStatus })
  });

  evaluateProject(surveyNo);
}

async function toggleOutageSimulation() {
  const res = await fetch('/api/land/toggle-outage', { method: 'POST' });
  const data = await res.json();
  isLandOutage = data.isOutageActive;
  document.getElementById('outageBtn').innerText = `Simulate 503 (${isLandOutage ? 'ACTIVE' : 'OFF'})`;
  evaluateProject(currentSession.registeredLandSurvey);
}

function reEvaluateCurrentState() {
  evaluateProject(currentSession?.registeredLandSurvey);
}

function logout() {
  currentSession = null;
  currentTxnData = null;
  document.getElementById('dashboardSection').style.display = 'none';
  document.getElementById('authSection').style.display = 'block';
  document.getElementById('identifierInput').value = '';
}
