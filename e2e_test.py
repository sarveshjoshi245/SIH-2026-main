"""
End-to-end verification sequence:
  1. Register citizen on port 5000 gateway
  2. Login (request OTP) via gateway
  3. Verify OTP
  4. Quick-decision via interop_backend (port from ports.json)
  5. Login to interop_backend (ensureInteropAuth equivalent)
  6. Submit verify-plant on interop_backend
"""
import requests
import json

# Addresses come from the repo-root ports.json (single source of truth).
import pathlib
_P = json.loads((pathlib.Path(__file__).resolve().parent / "ports.json").read_text(encoding="utf-8"))
GW = f"http://{_P['host']}:{_P['services']['portal']['port']}"
INTEROP = f"http://{_P['host']}:{_P['services']['interop']['port']}"

def step(n, label):
    print(f"\n{'='*60}")
    print(f"STEP {n}: {label}")
    print(f"{'='*60}")

# ── STEP 1: Register Citizen ──
step(1, "Register Citizen on Gateway (port 5000)")
r = requests.post(f"{GW}/api/auth/register", json={
    "firstName": "E2E",
    "lastName": "TestUser",
    "aadhaar": "111122223333",
    "pan": "E2ETP1234F",
    "mobile": "9000000001",
    "email": "e2e@test.gov.in"
})
print(f"  HTTP {r.status_code}")
print(f"  Body: {r.text[:500]}")

# ── STEP 2: Login (request OTP) ──
step(2, "Login (request OTP) via gateway POST /api/auth/login")
r = requests.post(f"{GW}/api/auth/login", json={
    "identifierType": "aadhaar",
    "identifierValue": "111122223333"
})
print(f"  HTTP {r.status_code}")
d2 = r.json()
print(f"  Body: {json.dumps(d2, indent=2)}")
txn_id_otp = d2.get("txnId", "")
print(f"  txnId: {txn_id_otp}")

# ── STEP 3: Verify OTP (demo OTP is 654321) ──
step(3, "Verify OTP (demo code 654321)")
r = requests.post(f"{GW}/api/auth/verify-otp", json={
    "txnId": txn_id_otp,
    "otp": "654321"
})
print(f"  HTTP {r.status_code}")
d3 = r.json()
print(f"  Body: {json.dumps(d3, indent=2)}")
gw_token = d3.get("token", "")
print(f"  Gateway token obtained: {'YES' if gw_token else 'NO'}")

# ── STEP 4: Quick Decision via interop_backend ──
step(4, f"Quick Decision (interop_backend {INTEROP})")
r = requests.post(f"{INTEROP}/api/interview/quick-decision", json={
    "project_type": "MANUFACTURING",
    "industry_type": "CHEMICAL",
    "location": {"district": "Pune", "state": "Maharashtra"},
    "land": {"required": True, "owned": True, "area_hectare": 4.5},
    "electricity": {"required": True, "required_load_kw": 500},
    "environment": {"industrial_emissions": True, "hazardous_waste": False}
})
print(f"  HTTP {r.status_code}")
d4 = r.json()
print(f"  Body: {json.dumps(d4, indent=2)}")
required_services = d4.get("required_services", [])
print(f"  Required services: {required_services}")

# ── STEP 5: Login to interop_backend (ensureInteropAuth equivalent) ──
step(5, "Login to interop_backend as ABC Industries (applicant@abcindustries.com)")
r = requests.post(f"{INTEROP}/api/auth/login", json={
    "email": "applicant@abcindustries.com",
    "password": "SecretPass123"
})
print(f"  HTTP {r.status_code}")
d5 = r.json()
print(f"  Body: {json.dumps(d5, indent=2)}")
interop_jwt = d5.get("access_token", "")
print(f"  Interop JWT obtained: {'YES' if interop_jwt else 'NO'}")

# ── STEP 6: Submit verify-plant on interop_backend ──
step(6, "Submit verify-plant (POST /api/projects/verify-plant)")
r = requests.post(f"{INTEROP}/api/projects/verify-plant", json={
    "project_name": "Chemical Manufacturing Unit",
    "organization_pan": "ABCDE1234F",
    "industry_type": "Chemical",
    "location_district": "Pune",
    "land_survey_number": "101",
    "electricity_application_number": "ELEC-2026-00101",
    "pollution_application_number": "MPCB-8821",
    "required_services": ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"]
}, headers={
    "Authorization": f"Bearer {interop_jwt}"
})
print(f"  HTTP {r.status_code}")
d6 = r.json()
print(f"  Body: {json.dumps(d6, indent=2)}")
txn_id = d6.get("transaction_id", "NOT FOUND")
print(f"\n  >>> transaction_id: {txn_id}")
print(f"\n{'='*60}")
print("E2E SEQUENCE COMPLETE")
print(f"{'='*60}")
