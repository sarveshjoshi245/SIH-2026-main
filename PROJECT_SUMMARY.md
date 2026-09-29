# Government Interoperability Platform & RAG Decision Engine
### Smart India Hackathon (SIH 2026) — Problem Statement SIH26129

---

## 1. Executive Summary

This project is a high-fidelity, resilient **Government Interoperability Platform** paired with an intelligent **RAG Conversational Intake & Decision Engine**. 

In real-world single-window clearance ecosystems, setting up an industrial facility (manufacturing plant, warehouse, IT park) requires interacting with multiple departmental systems that operate in silos, speak completely different data schemas (legacy formats), and have strict regulatory dependency orders.

This platform solves this problem by:
1. **Conversational RAG Intake**: Asking applicants targeted questions about their industrial project and deterministically calculating exactly which departmental clearances are legally required.
2. **Topological Dependency Ordering**: Grouping clearances into execution waves (e.g., Land and Electricity can be verified concurrently in Wave 1, while Pollution Consent depends on Land and must execute in Wave 2).
3. **Deterministic Interoperability Gateway**: Normalizing legacy departmental APIs (Land, Electricity, Pollution) into a unified Canonical Data Model.
4. **PAN-Strict Identity Governance**: Eliminating name ambiguity by joining all departmental records strictly on the organization's Permanent Account Number (PAN).
5. **DPDP Act Compliance & Masked Audits**: Requiring explicit user consent before querying departmental facts and masking sensitive identifiers in audit trails (`AB****34F`).
6. **Fault Tolerance & Resilience**: Implementing Circuit Breakers and AI-assisted Schema Drift Detection to prevent gateway crashes when downstream department systems evolve or fail.

---

## 2. High-Level Architecture

```text
                           APPLICANT / USER
                                  │
                                  ▼
     ┌─────────────────────────────────────────────────────────┐
     │          INTEROP BACKEND GATEWAY (:8000)                 │
     │  • Interactive question sequence (MCQ-first)           │
     │  • Regulatory explanation retrieval                     │
     │  • Deterministic service decision logic                 │
     │  • Topological execution plan (Wave 1, Wave 2)          │
     └────────────────────────────┬────────────────────────────┘
                                  │ Required services & plan
                                  ▼
     ┌─────────────────────────────────────────────────────────┐
     │             INTEROP BACKEND GATEWAY (:5000)             │
     │  • JWT Authentication & RBAC (Applicant, Admin, Auditor)│
     │  • Explicit Departmental Consent Verification           │
     │  • Legacy-to-Canonical Rule-Based Schema Normalizer     │
     │  • Clearance Decision Policy Engine                     │
     │  • Circuit Breaker (Closed / Half-Open / Open)          │
     │  • AI Schema Drift Detector & Semantic Suggester        │
     │  • Masked Audit Logging                                 │
     └──────────────┬─────────────┬─────────────┬──────────────┘
                    │             │             │ Parallel Async Calls
       ┌────────────┘             │             └────────────┐
       ▼                          ▼                          ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   LAND API   │          │ ELECTRICITY  │          │  POLLUTION   │
│   (:4000)    │          │  API (:8001) │          │  API (:4002) │
│ (Node Express│          │  (FastAPI +  │          │ (Node Express│
│   Legacy     │          │    SQLite)   │          │   Legacy     │
│   Marathi    │          │  Discom/MSEDCL│         │    MPCB      │
│   Schema)    │          │    Schema)   │          │   Schema)    │
└──────────────┘          └──────────────┘          └──────────────┘
```

---

## 3. Microservice Breakdown

### A. RAG Intake & Decision Engine (`rag-service` — Port `8001`) [legacy]
> ⚠️ Note: rag-service is not part of the active `ports.json` setup. The interop_backend runs on **port 8000** and electricity on **8001**.
- **Technology**: Python 3.12, FastAPI, Pydantic v2.
- **Role**: Conducts a structured conversational interview to collect project requirements (industry type, location, land area, power load, hazardous waste/emissions).
- **Key Guarantee**: The LLM / RAG layer **never** makes regulatory approval decisions hallucinating services. It collects profile attributes, while pure deterministic code computes required services and execution waves.
- **Endpoints**:
  - `POST /interview/message` — Interactive Q&A.
  - `GET /interview/{session_id}/decision` — Final decision & wave plan.
  - `GET /health` — Service health.

### B. Interoperability Gateway (`interop_backend` — Port `5000`)
- **Technology**: Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite (or PostgreSQL), PyJWT.
- **Role**: Central orchestrator. Handles user login, verifies active user consent for Land/Electricity/Pollution, executes parallel calls to departments, normalizes payloads, and logs tamper-proof masked audit trails.
- **Endpoints**:
  - `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
  - `POST /api/consent`, `GET /api/consent/my`
  - `POST /api/projects/verify-plant` — End-to-end multi-department clearance check.
  - `GET /api/departments/health` — Circuit breaker states for all 3 departments.
  - `POST /api/schema/detect` — AI schema drift resolution.
  - `GET /api/audit` — Access audit trails with masked PANs.

### C. Land Records Department API (`land_api` — Port `4000`)
- **Technology**: Node.js, Express.js.
- **Data Model**: Legacy land records using native terminology (`gtn` for survey number, `malak_pan`, `jamabandi` for status, `kshetra` for area in hectares).
- **Endpoints**:
  - `GET /api/land/records/:surveyNumber`
  - `POST /api/land/verify`
  - `GET /api/land/status/:surveyNumber`

### D. Electricity Department API (`electricity_department_api` — Port `8001`)
- **Technology**: Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite.
- **Data Model**: Legacy Discom attributes (`appl_no`, `cust_pan`, `load_sanc`, `appl_stat`, `meter_stat`, `conn_stat`, `dues_flag`).
- **Features**: Includes machine-to-machine API key scope enforcement and an Admin State Mutation endpoint (`/api/admin/set-state`) to simulate application status progression.
- **Endpoints**:
  - `POST /api/electricity/verify`
  - `GET /api/electricity/status/:appl_no`
  - `POST /api/admin/set-state`

### E. Pollution / Environment Department API (`pollution_api` — Port `4002`)
- **Technology**: Node.js, Express.js.
- **Data Model**: Legacy MPCB structure (`application_no`, `industry_pan`, `consent_type` CTE/CTO, `consent_status`, `compliance_status`, `air_emission_category`).
- **Endpoints**:
  - `GET /api/pollution/applications/:applicationNo`
  - `GET /api/pollution/status/:applicationNo`
  - `POST /api/pollution/verify`

---

## 4. Key Workflows & Innovation Highlights

### 1. PAN-First Identity Resolution
Traditional portals match company names with string matching (which frequently fails due to abbreviations, e.g. "ABC Industries" vs "ABC Industries Pvt Ltd"). This platform strictly verifies that the enterprise PAN attached to the authenticated session matches the PAN in every departmental record.

### 2. Explicit Consent Architecture
Before a single packet is dispatched to a department API, the platform checks the database for active consent granted by the company owner for that specific purpose and department, upholding DPDP Act privacy principles.

### 3. Graceful Resilience & Circuit Breaking
If one department API (e.g. Pollution) suffers high latency or downtime, the Circuit Breaker trips to `OPEN`. The gateway does not crash; it resolves available facts, flags the failed department as `UNAVAILABLE`, sets overall status to `WAITING`, and gives the applicant clear retry guidance.

### 4. Schema Drift Simulator & AI Resolver
Government APIs frequently change variable names without warning (e.g., `appl_no` ➔ `application_no`). The gateway's schema drift engine detects unmapped incoming keys and leverages semantic matching to suggest canonical bindings to administrators.

---

## 5. Seed Demonstration Personas & Test Data

### Authentic Users:
- **Applicant**: `applicant@abcindustries.com` / `SecretPass123` (PAN: `ABCDE1234F`)
- **Admin**: `admin@interop.gov.in` / `AdminPass456`
- **Auditor**: `auditor@interop.gov.in` / `AuditPass789`

### Valid Golden Combination (Produces RESOLVED Status):
- **Organization PAN**: `ABCDE1234F`
- **Land Survey / GTN**: `101`
- **Electricity App No**: `ELEC-2026-00101`
- **Pollution App No**: `MPCB-8821`

---

## 6. How to Run & Inspect

### Startup Commands (if running manually):
```bash
# Terminal 1 - Land API
cd land_api && node server.js                     # Port 4000

# Terminal 2 - Pollution API
cd pollution_api && node server.js                # Port 4002

# Terminal 3 - Electricity API
cd electricity_department_api && python run_dev.py    # Port 8001 (from ports.json)

# Terminal 4 - Interoperability Gateway
cd interop_backend && python run_dev.py               # Port 8000 (from ports.json)

# Terminal 5 - RAG Intake Service
cd rag-service && uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Swagger Documentation:
- Interop Backend: `http://localhost:8000/docs`
- Electricity Department: `http://localhost:8001/docs`

### Automated Test Suite:
```bash
# 85 Total Unit, Integration & Workflow Tests
python -m pytest rag-service/tests/ -v
python -m pytest electricity_department_api/tests/ -v
python -m pytest interop_backend/tests/ -v
```
*(All 85 tests passing)*
