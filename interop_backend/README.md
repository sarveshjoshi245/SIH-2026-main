# Government Interoperability Platform Backend
### SIH 2026 — Problem Statement SIH26129

> **A secure, deterministic, and resilient API gateway that connects heterogeneous departmental systems through a unified canonical data model.**

---

## Architecture Overview

```
                       ENTERPRISE APPLICANT
                              │  JWT
                              ▼
                  ┌─────────────────────────┐
                  │  INTEROP BACKEND :5000  │
                  │  (This Service)          │
                  │  • Consent Gate          │
                  │  • PAN Identity Check   │
                  │  • Rule-Based Mapper    │
                  │  • Policy Engine        │
                  │  • Circuit Breaker      │
                  │  • Audit Logger         │
                  └────────────┬────────────┘
                               │ parallel async
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                   ▼
    LAND API :4000    ELECTRICITY API :8001   POLLUTION API :4002
    (Node.js)         (FastAPI)               (Node.js)
```

---

## Core Features

| Feature | Description |
|---|---|
| **JWT Auth** | Role-based (APPLICANT / GOVT_ADMIN / AUDITOR) |
| **Consent Governance** | Explicit per-department consent before any data access |
| **PAN-Based Identity** | Cross-department join strictly on PAN — never on company name |
| **Rule-Based Mapper** | Deterministic `LAND / ELECTRICITY / POLLUTION` → Canonical Model transformation |
| **Policy Engine** | Evaluates all 3 departmental facts to compute overall clearance status |
| **Circuit Breakers** | Stateful Closed/Open/Half-Open per department — tolerates partial outages |
| **AI Drift Resolver** | Detects unmapped fields, computes fuzzy-semantic similarity, suggests canonical mapping |
| **Masked Audit Trail** | PAN masked as `AB****34F` in all audit logs |

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | POST | Public | Register enterprise user |
| `/api/auth/login` | POST | Public | Obtain JWT |
| `/api/auth/me` | GET | JWT | Profile |
| `/api/consent` | POST | JWT | Grant departmental consent |
| `/api/consent/my` | GET | JWT | List active consents |
| `/api/projects/verify-plant` | POST | JWT | **Main endpoint** — orchestrates all 3 departments |
| `/api/projects/transactions` | GET | JWT | List transactions |
| `/api/projects/transactions/{id}` | GET | JWT | Detailed execution breakdown |
| `/api/canonical/transform` | POST | Public | Test schema mapping directly |
| `/api/schema/detect` | POST | Public | Detect schema drift in payload |
| `/api/schema/approve-drift` | POST | Admin | Approve AI mapping suggestion |
| `/api/departments/health` | GET | Public | Check all 3 department connectivity |
| `/api/audit` | GET | JWT | Platform audit trail |

Interactive docs: **`http://localhost:8000/docs`**

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+ (for Land and Pollution APIs)

### 1. Start Department APIs

```bash
# Terminal 1 — Land API
cd land_api && npm install && node server.js

# Terminal 2 — Electricity API
cd electricity_department_api && pip install -r requirements.txt && python run_dev.py  # port 8001

# Terminal 3 — Pollution API
cd pollution_api/pollution_api && npm install && node server.js
```

### 2. Start Interop Backend

```bash
cd interop_backend
pip install -r requirements.txt
cp .env.example .env
python run_dev.py  # port 8000 — reads from ports.json
```

### 3. Run Tests

```bash
cd interop_backend
python -m pytest -v
# Expected: 17 passed ✅
```

---

## Docker (All Services)

```bash
cd interop_backend
docker-compose up --build
```

Services will start at:
- Interop Backend: http://localhost:8000
- Land API: http://localhost:4000
- Electricity API: http://localhost:8001
- Pollution API: http://localhost:4002

---

## End-to-End Flow Example

### 1. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"applicant@abcindustries.com","password":"SecretPass123"}'
```

### 2. Verify Plant Clearance
```bash
curl -X POST http://localhost:5000/api/projects/verify-plant \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "ABC Chakan Expansion Unit",
    "organization_pan": "ABCDE1234F",
    "land_survey_number": "101",
    "electricity_application_number": "ELEC-2026-00101",
    "pollution_application_number": "MPCB-8821",
    "industry_type": "Chemical"
  }'
```

**Response** includes:
```json
{
  "transaction_id": "TXN-20260902-AB1C2D",
  "overall_clearance_status": "RESOLVED",
  "pan_identity_verified": true,
  "department_checks": [...],
  "canonical_project_state": {...},
  "recommended_next_action": "All departmental prerequisites are satisfied."
}
```

---

## Default Seeded Accounts

| Email | Password | Role | PAN |
|---|---|---|---|
| applicant@abcindustries.com | SecretPass123 | APPLICANT | ABCDE1234F |
| applicant@xyzmfg.com | SecretPass123 | APPLICANT | FGHIJ5678K |
| admin@interop.gov.in | AdminSecret888 | GOVT_ADMIN | GOVAA0000A |
| auditor@sih.gov.in | AuditorPass999 | AUDITOR | GOVAA0000B |

---

## Project Structure

```
interop_backend/
├── app/
│   ├── main.py                  # FastAPI app + lifespan seeding
│   ├── config.py                # Pydantic settings
│   ├── database.py              # SQLAlchemy engine
│   ├── adapters/                # Department HTTP clients
│   │   ├── base.py              # Retry + Circuit Breaker base
│   │   ├── land_adapter.py
│   │   ├── electricity_adapter.py
│   │   └── pollution_adapter.py
│   ├── auth/
│   │   ├── jwt_handler.py       # bcrypt hashing + JWT encode/decode
│   │   └── dependencies.py      # FastAPI dependency injectors
│   ├── engine/
│   │   ├── circuit_breaker.py   # Stateful CB: Closed/Open/Half-Open
│   │   ├── mapper.py            # Rule-based schema transformation
│   │   ├── policy_engine.py     # Cross-department PAN + prerequisite eval
│   │   ├── ai_drift_resolver.py # AI schema drift detection
│   │   └── workflow_engine.py   # Orchestration coordinator
│   ├── models/                  # SQLAlchemy ORM models
│   ├── routers/                 # FastAPI route handlers
│   └── schemas/                 # Pydantic request/response models
└── tests/
    ├── conftest.py              # TestClient + Mock adapters
    ├── test_auth.py
    ├── test_consent.py
    ├── test_mapper.py
    ├── test_workflow.py
    ├── test_resilience.py
    ├── test_schema_drift.py
    └── test_audit.py
```
