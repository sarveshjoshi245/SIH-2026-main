# Electricity Distribution Department API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=Python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=SQLAlchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?style=flat&logo=SQLite&logoColor=white)](https://www.sqlite.org/)

> **Synthetic Data & Prototype Disclaimer**  
> All records, PANs, consumer numbers, addresses, and API credentials in this repository are **synthetic** and created solely for testing, demonstration, and the Smart India Hackathon. This service is **not** an official government API and is not affiliated with any state electricity distribution board.

---

## 1. Project Overview

The **Electricity Distribution Department API** is a standalone, high-fidelity backend service simulating a state-level electricity board (e.g., MSEDCL / Discom). 

In real-world single-window clearances, an industrial applicant applying for factory establishment must secure power connectivity. This service exposes **authoritative departmental facts**—such as application status, sanctioned load, inspection status, meter installation, energization status, and outstanding dues—through legacy/department-native schemas.

---

## 2. Why a Standalone Electricity Department API?

In enterprise government interoperability architectures:
- **Separation of Concerns:** The Electricity Department only knows electricity facts. It does **not** know about MPCB (Pollution Control), Land Records, or applicant workflow orchestration.
- **Fact Provider vs. Workflow Interpreter:** The Electricity API provides authoritative data (`Connection Status = ENERGIZED`, `Dues = False`). The external interoperability layer interprets whether this fulfills an industrial clearance prerequisite.
- **Department-Native Schemas:** Real departmental APIs return internal field keys (`appl_no`, `load_sanc`, `dues_flag`) rather than normalized canonical models.

---

## 3. Architecture & Ecosystem Diagram

```text
    COMPANY / APPLICANT (e.g. ABC Industries Pvt Ltd)
                           │
                           ▼
             INTEROPERABILITY PLATFORM
                           │
                           │ Authorized API Requests (X-API-Key)
                           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              ELECTRICITY DISTRIBUTION API                   │
  │                                                             │
  │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
  │  │ Machine-to-Machine Auth │   │ Department-Native       │  │
  │  │ & Scope Enforcement     │   │ Legacy Schema Provider  │  │
  │  └─────────────────────────┘   └─────────────────────────┘  │
  │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
  │  │ Identity Verification   │   │ Lightweight Polling     │  │
  │  │ (PAN + App Matching)    │   │ (/status/{app_no})      │  │
  │  └─────────────────────────┘   └─────────────────────────┘  │
  │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
  │  │ Schema Drift Simulator  │   │ Chaos & Fault Injection │  │
  │  │ (15-20% field variation)│   │ (503s & Latency Delays) │  │
  │  └─────────────────────────┘   └─────────────────────────┘  │
  │  ┌─────────────────────────┐   ┌─────────────────────────┐  │
  │  │ Admin State Mutation    │   │ Structured Audit Trail  │  │
  │  │ (Demo Orchestration)    │   │ (Masked PANs & Latency) │  │
  │  └─────────────────────────┘   └─────────────────────────┘  │
  │                                                             │
  │                  Persistent SQLite Database                 │
  │     (applications, connections, consumers, audit_logs)     │
  └─────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Stack

- **Framework:** FastAPI (Python 3.12+)
- **ORM / Database:** SQLAlchemy 2.0 with persistent SQLite (`electricity_department.db`)
- **Data Validation & Settings:** Pydantic v2 & `pydantic-settings`
- **Server:** Uvicorn ASGI
- **Testing:** Pytest, HTTPX TestClient
- **Containerization:** Docker & Docker Compose

---

## 5. API Endpoints Reference

| Method | Endpoint | Auth Required | Scope Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | No | None | Public health check and service uptime |
| `GET` | `/api/electricity/applications/{application_number}` | Yes | `/api/electricity/*` | Retrieve raw application facts in legacy schema |
| `GET` | `/api/electricity/connections/{consumer_number}` | Yes | `/api/electricity/*` | Retrieve existing consumer connection facts |
| `POST` | `/api/electricity/verify` | Yes | `/api/electricity/*` | Verify PAN + application number; returns facts |
| `GET` | `/api/electricity/status/{application_number}` | Yes | `/api/electricity/*` | Lightweight polling status for async dependencies |
| `POST` | `/api/admin/set-state` | Yes | `/api/admin/*` | **Demo Only:** Mutate departmental application states |
| `GET` | `/api/audit` | Yes | `/api/audit` | Retrieve access logs with masked PANs |

Interactive Swagger documentation is available at `http://localhost:8001/docs` and OpenAPI JSON at `http://localhost:8001/openapi.json`.

---

## 6. Authentication & API Key Scopes

All protected endpoints require the HTTP header:
```http
X-API-Key: <key>
```

### Pre-configured Seed Consumers

| Consumer ID | Simulated API Key | Allowed Scopes | Description |
| :--- | :--- | :--- | :--- |
| `INTEROP-PLATFORM` | `elec_live_interop_key_991` | `["/api/electricity/*", "/api/audit"]` | Main interoperability integration engine |
| `INDUSTRIAL-CLEARANCE` | `elec_live_clearance_key_552` | `["/api/electricity/*"]` | External single-window clearance portal |
| `DEMO-FRONTEND` | `elec_demo_key_101` | `["/api/electricity/*", "/api/admin/*", "/api/audit"]` | Demo UI dashboard with admin controls |
| `ADMIN-CLIENT` | `elec_admin_secret_key_888` | `["*"]` | Full administrative root access |

### Error Responses
- **401 Unauthorized:** Missing or invalid API key.
- **403 Forbidden:** Valid API key lacking required scope for endpoint.

---

## 7. Department-Native vs Canonical Schema

The Electricity API intentionally returns legacy abbreviated field names. The external interoperability adapter maps these to canonical fields.

### Department Legacy Response
```json
{
  "appl_no": "ELEC-2026-00102",
  "cons_no": null,
  "cust_name": "XYZ Manufacturing Pvt Ltd",
  "cust_pan": "FGHIJ5678K",
  "load_req": "750",
  "load_unit": "KW",
  "load_sanc": "750",
  "load_sanc_unit": "KW",
  "cat_code": "HT-IND",
  "conn_type": "INDUSTRIAL",
  "appl_stat": "PENDING",
  "insp_stat": "PENDING",
  "meter_stat": "NOT_INSTALLED",
  "conn_stat": "NOT_CONNECTED",
  "dues_flag": false,
  "sec_dep": "PENDING"
}
```

### Canonical Target (Constructed by external adapter, NOT this API)
```json
{
  "application_number": "ELEC-2026-00102",
  "consumer_number": null,
  "applicant": "XYZ Manufacturing Pvt Ltd",
  "organization_pan": "FGHIJ5678K",
  "requested_load_kw": 750,
  "sanctioned_load_kw": 750,
  "supply_category": "HT-IND",
  "connection_type": "INDUSTRIAL",
  "application_status": "PENDING",
  "inspection_status": "PENDING",
  "meter_status": "NOT_INSTALLED",
  "connection_status": "NOT_CONNECTED",
  "outstanding_dues": false,
  "security_deposit_status": "PENDING"
}
```

---

## 8. Seed Applications

| Application Number | Company Name | PAN | Category | App Status | Inspection | Meter | Connection | Dues | Demo Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ELEC-2026-00101` | ABC Industries Pvt Ltd | `ABCDE1234F` | HT-IND (500 kW) | APPROVED | COMPLETED | INSTALLED | ENERGIZED | `false` | **Success:** Prerequisite satisfied |
| `ELEC-2026-00102` | XYZ Manufacturing Pvt Ltd | `FGHIJ5678K` | HT-IND (750 kW) | PENDING | PENDING | NOT_INSTALLED | NOT_CONNECTED | `false` | **Async Demo:** Polling & State Mutation |
| `ELEC-2026-00103` | DEF Industries Pvt Ltd | `LMNOP9012Q` | HT-IND (800 kW) | APPROVED | COMPLETED | INSTALLED | NOT_CONNECTED | `true` | **Dues Warning:** Approved but dues exist |
| `ELEC-2026-00104` | RST Industries Pvt Ltd | `RSTUV3456W` | LT-IND (300 kW) | REJECTED | FAILED | NOT_INSTALLED | NOT_CONNECTED | `false` | **Rejection:** Inspection failed reason |
| `ELEC-2026-00105` | ABC Industries Pvt Ltd | `ABCDE1234F` | LT-IND (250 kW) | APPROVED | COMPLETED | INSTALLED | ENERGIZED | `true` | **Same PAN / Dues:** Dues check demo |
| `ELEC-2026-00106` | PQR Industries Pvt Ltd | `PQRWX7890Y` | HT-IND (600 kW) | UNDER_INSPECTION | IN_PROGRESS | NOT_INSTALLED | NOT_CONNECTED | `false` | **Intermediate:** In-progress state |

---

## 9. Department Status Model & State Transitions

### Allowed Native Enums
- **Application Status:** `SUBMITTED`, `UNDER_SCRUTINY`, `PENDING`, `APPROVED`, `REJECTED`, `UNDER_INSPECTION`
- **Inspection Status:** `NOT_REQUIRED`, `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`
- **Meter Status:** `NOT_INSTALLED`, `INSTALLATION_SCHEDULED`, `INSTALLED`
- **Connection Status:** `NOT_CONNECTED`, `READY_FOR_ENERGIZATION`, `ENERGIZED`, `DISCONNECTED`
- **Security Deposit:** `PENDING`, `PAID`, `WAIVED`, `NOT_REQUIRED`

```text
SUBMITTED ──► UNDER_SCRUTINY ──► PENDING ──► APPROVED ──► UNDER_INSPECTION ──► COMPLETED ──► INSTALLED ──► ENERGIZED
     │              │                                              │
     ▼              ▼                                              ▼
  REJECTED       REJECTED                                    INSPECTION FAILED (REJECTED)
```

---

## 10. Schema Drift Simulation

Real department legacy APIs periodically change variable naming in minor updates.
- **Config:** `SCHEMA_DRIFT_RATE=0.20` (20% chance) or forced via header `X-Force-Schema-Drift: true`.
- **Drift Mappings:**
  - `appl_no` ➔ `application_no`
  - `cust_name` ➔ `consumer_name`
  - `load_sanc` ➔ `sanctioned_load`
  - `appl_stat` ➔ `application_status`
  - `conn_stat` ➔ `connection_status`
- **Integrity Rule:** Only field names drift. Data values and semantic meaning are strictly preserved.

---

## 11. Chaos / Fault Injection

Configured via environment variables to simulate transport-level failures and delays for resilience testing:
- `CHAOS_ENABLED=true`
- Returns HTTP 503:
```json
{
  "status": "DEPARTMENT_UNAVAILABLE",
  "department": "ELECTRICITY_DISTRIBUTION",
  "message": "Electricity Department systems are temporarily unavailable",
  "retryable": true,
  "transaction_id": "ELEC-TXN-8F123A"
}
```

---

## 12. Demo Scenarios & Walkthroughs

### Scenario 1: Successful Verification
```bash
curl -X POST http://localhost:8001/api/electricity/verify \
  -H "X-API-Key: elec_live_interop_key_991" \
  -H "Content-Type: application/json" \
  -d '{"application_number": "ELEC-2026-00101", "pan": "ABCDE1234F"}'
```
**Response:** `HTTP 200`, `pan_match: true`, `appl_stat: "APPROVED"`, `conn_stat: "ENERGIZED"`.

### Scenario 2: Asynchronous Workflow & Admin State Transition
1. Initial verification of `ELEC-2026-00102`:
```bash
curl -X GET http://localhost:8001/api/electricity/status/ELEC-2026-00102 \
  -H "X-API-Key: elec_live_interop_key_991"
```
**Response:** `appl_stat: "PENDING"`, `retryable: true`.

2. Admin state mutation:
```bash
curl -X POST http://localhost:8001/api/admin/set-state \
  -H "X-API-Key: elec_admin_secret_key_888" \
  -H "Content-Type: application/json" \
  -d '{
    "application_number": "ELEC-2026-00102",
    "application_status": "APPROVED",
    "inspection_status": "COMPLETED",
    "meter_status": "INSTALLED",
    "connection_status": "ENERGIZED"
  }'
```

3. Polling status again:
```bash
curl -X GET http://localhost:8001/api/electricity/status/ELEC-2026-00102 \
  -H "X-API-Key: elec_live_interop_key_991"
```
**Response:** `appl_stat: "APPROVED"`, `conn_stat: "ENERGIZED"`, `retryable: false`.

### Scenario 3: Rejected Application
```bash
curl -X POST http://localhost:8001/api/electricity/verify \
  -H "X-API-Key: elec_live_interop_key_991" \
  -H "Content-Type: application/json" \
  -d '{"application_number": "ELEC-2026-00104", "pan": "RSTUV3456W"}'
```
**Response:** `appl_stat: "REJECTED"`, `rej_reason: "Electrical infrastructure inspection failed"`.

### Scenario 4: Identity Mismatch (Wrong PAN)
```bash
curl -X POST http://localhost:8001/api/electricity/verify \
  -H "X-API-Key: elec_live_interop_key_991" \
  -H "Content-Type: application/json" \
  -d '{"application_number": "ELEC-2026-00101", "pan": "ZZZZZ9999Z"}'
```
**Response:** `HTTP 200`, `pan_match: false`.

---

## 13. Audit Logging & Privacy

- All API access is recorded in `audit_logs`.
- Full PAN is **never** logged in clear text; it is masked (e.g. `AB****34F`).
- API keys are never stored in log records.
- Retrieve audit trails:
```bash
curl -X GET "http://localhost:8001/api/audit?limit=10" \
  -H "X-API-Key: elec_live_interop_key_991"
```

---

## 14. Quickstart & Local Setup

### Without Docker

```bash
# 1. Navigate to directory
cd electricity_department_api

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

### With Docker

```bash
cd electricity_department_api
docker compose up --build -d
```

Open Swagger UI at `http://localhost:8001/docs`.

---

## 15. Running Automated Tests

```bash
cd electricity_department_api
pytest -v
```
