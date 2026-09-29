# 🏗️ Technical Architecture Diagram
### Government Interoperability Platform & RAG Decision Engine
**Smart India Hackathon (SIH) 2026 — Problem Statement SIH26129**

---

## 1. 🧑‍💼 User / Actor Layer

- **Applicant** — Industry Owner seeking departmental clearances
- **Admin** — Government Administrator
- **Auditor** — Compliance Auditor
- **Machine Client** — API key–based M2M (Machine-to-Machine) access

---

## 2. 🌐 Presentation / Client Layer

- **Web Portal** — Static HTML/CSS/JS frontend (served from `server/public/`)
  - Login Page (`login.html`)
  - Dashboard
  - e-KYC Interface
- **Swagger UI** — `/docs` endpoint on each FastAPI microservice (auto-generated)

---

## 3. 🤖 RAG Intake & Decision Engine — Port `8001`

**Technology:** Python 3.12 · FastAPI · Pydantic v2 · FAISS Vector Store

| Component | Detail |
|---|---|
| Conversational Interview Module | MCQ-first structured Q&A session per applicant |
| Knowledge Base (FAISS Index) | Regulatory document embeddings for retrieval |
| RAG Retriever | Semantic similarity search on regulation corpus |
| Deterministic Decision Engine | Rule-based logic — computes required clearances |
| Topological Wave Planner | Wave 1 (Land + Electricity in parallel) → Wave 2 (Pollution) |
| Session Manager | Stateful interview sessions per applicant |

**Endpoints:**
- `POST /interview/message` — Interactive Q&A
- `GET /interview/{session_id}/decision` — Final decision & wave plan
- `GET /health` — Service health check

---

## 4. 🔀 Interoperability Gateway — Port `5000`

**Technology:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · SQLite/PostgreSQL · PyJWT

| Sub-Component | Role |
|---|---|
| JWT Auth Module | Login, Register, Token validation |
| RBAC Engine | Role enforcement: Applicant / Admin / Auditor |
| PAN Identity Resolver | Strict PAN-based org identity — no fuzzy name matching |
| Explicit Consent Manager | Checks active DPDP-compliant consent before any dept. call |
| Canonical Data Model | Unified schema normalizing all departmental data |
| Schema Normalizer (Rule-Based) | Translates legacy field names → canonical fields |
| AI Schema Drift Detector | Detects unmapped keys, suggests semantic field bindings |
| Orchestration Engine | Parallel async dispatch to dept. APIs per wave plan |
| Circuit Breaker | States: CLOSED → HALF-OPEN → OPEN per department |
| Clearance Decision Policy Engine | Final verdict: APPROVED / REJECTED / WAITING / UNAVAILABLE |
| Masked Audit Logger | Tamper-proof logs with masked PANs (AB****34F) |
| Adapters Layer | Department-specific API client adapters (Land, Electricity, Pollution) |

**Key Endpoints:**
- `POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me`
- `POST /api/consent` · `GET /api/consent/my`
- `POST /api/projects/verify-plant`
- `GET /api/departments/health`
- `POST /api/schema/detect`
- `GET /api/audit`

---

## 5. 🏢 Departmental Microservices (Legacy APIs)

### A. Land Records API — Port `4000`

**Technology:** Node.js · Express.js

| Element | Detail |
|---|---|
| Data Schema | Legacy Marathi / Government format |
| Key Fields | `gtn` (survey no.), `malak_pan`, `jamabandi` (status), `kshetra` (area in hectares) |
| Authentication | API-key based |

**Endpoints:** `GET /api/land/records/:surveyNumber` · `POST /api/land/verify` · `GET /api/land/status/:surveyNumber`

---

### B. Electricity Department API — Port `8001`

**Technology:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · SQLite

| Element | Detail |
|---|---|
| Data Schema | Legacy Discom / MSEDCL format |
| Key Fields | `appl_no`, `cust_pan`, `load_sanc`, `appl_stat`, `meter_stat`, `conn_stat`, `dues_flag` |
| Special Feature | Admin State Mutation endpoint to simulate application status progression |

**Endpoints:** `POST /api/electricity/verify` · `GET /api/electricity/status/:appl_no` · `POST /api/admin/set-state`

---

### C. Pollution / Environment Department API — Port `4002`

**Technology:** Node.js · Express.js

| Element | Detail |
|---|---|
| Data Schema | Legacy MPCB format |
| Key Fields | `application_no`, `industry_pan`, `consent_type` (CTE/CTO), `consent_status`, `compliance_status`, `air_emission_category` |

**Endpoints:** `GET /api/pollution/applications/:applicationNo` · `GET /api/pollution/status/:applicationNo` · `POST /api/pollution/verify`

---

## 6. 🗄️ Data / Storage Layer

| Store | Used By | Technology |
|---|---|---|
| Interop Platform DB | Gateway (auth, consent, audit logs) | SQLite / PostgreSQL (SQLAlchemy ORM) |
| Electricity DB | Electricity API | SQLite (SQLAlchemy ORM) |
| FAISS Vector Index | RAG Service | FAISS (flat file index) |
| Regulatory Knowledge Base | RAG Service | Markdown / text document corpus |
| Land Records Store | Land API | In-memory / JSON flat store |
| Pollution Records Store | Pollution API | In-memory / JS store (data/store.js) |

---

## 7. 🔐 Security & Compliance Layer

| Mechanism | Detail |
|---|---|
| Authentication | JWT Bearer Tokens (PyJWT) |
| Authorization | RBAC — 3 roles: Applicant, Admin, Auditor |
| Identity Governance | PAN-strict identity resolution — no fuzzy name matching |
| Data Privacy | DPDP Act — explicit user consent before any dept. data query |
| Audit Trail | Masked PAN logs (AB****34F) — tamper-proof |
| M2M API Security | API key scope enforcement (Electricity Department API) |

---

## 8. ⚡ Resilience & Fault Tolerance Layer

| Pattern | Detail |
|---|---|
| Circuit Breaker | Per-department state machine: CLOSED / HALF-OPEN / OPEN |
| Parallel Async Execution | Concurrent department API calls via Python asyncio |
| Schema Drift Detection | AI-assisted detection + semantic field mapping suggestions |
| Graceful Degradation | Returns partial results + WAITING status on department failure |

---

## 9. 🧪 Testing Layer

| Scope | Tool |
|---|---|
| RAG Service Unit & Integration Tests | pytest |
| Electricity API Unit & Integration Tests | pytest |
| Interop Gateway Unit & Integration Tests | pytest |
| **Total: 85 Tests (All Passing)** | pytest |

**Test Commands:**
```bash
python -m pytest rag-service/tests/ -v
python -m pytest electricity_department_api/tests/ -v
python -m pytest interop_backend/tests/ -v
```

---

## 10. 🚀 Deployment / Infrastructure Layer

| Component | Detail |
|---|---|
| Containerization | Docker (Dockerfile per microservice) |
| Orchestration | docker-compose.yml |
| Interoperability Backend (interop_backend) | Port 8000 |
| Electricity Department API | Port 8001 |
| Land Records API | Port 4000 |
| Pollution Department API | Port 4002 |
| Static Web Portal | Express.js — Port 5000 (server/public/) |

**Swagger Documentation:**
- Interop Backend: `http://localhost:8000/docs`
- Electricity Department: `http://localhost:8001/docs`

---

## 11. 📊 High-Level Data Flow

```
APPLICANT
    │
    ▼
Interop Backend (:8000)
    │  Conversational Q&A → Regulatory decision → Wave plan
    │
    ▼
Interoperability Gateway (:5000)
    │  JWT Auth → Consent Check → PAN Resolution → Parallel Dispatch
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
Land API (:4000)  Electricity API (:8001)  Pollution API (:4002)
[Marathi Schema]  [Discom/MSEDCL Schema]   [MPCB Schema]
    │                  │                  │
    └──────────────────┴──────────────────┘
                        │
                        ▼
             Schema Normalization
             (Legacy → Canonical)
                        │
                        ▼
             Clearance Decision Engine
             (APPROVED / REJECTED / WAITING)
                        │
                        ▼
             Masked Audit Log + Response to Applicant
```

---

*Generated for SIH 2026 — Government Interoperability Platform*
