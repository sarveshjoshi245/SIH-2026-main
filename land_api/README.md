# Land Records Department API (Simulated)

A deliberately legacy-shaped, independently-owned demo government API — the
first departmental building block for the **Government Interoperability
Layer** SIH project. It exists to be *consumed* by an interoperability
adapter, so it intentionally keeps its own field names (`gtn`, `malak_name`,
`jamabandi`, ...) instead of already speaking the platform's canonical
schema.

## Setup

```bash
npm install
npm start
# -> Land Department API (simulated) listening on http://localhost:4000
```

## Demo API keys

| Consumer | API Key | Permissions |
|---|---|---|
| INTEROP-PLATFORM | `interop-demo-key-001` | records, status, verify, mutation admin, audit, schema-drift detection |
| MPCB-CONSENT | `mpcb-demo-key-002` | status, verify |
| ELECTRICITY-DISCOM | `discom-demo-key-003` | status only |

These are synthetic demo credentials, not real government credentials.

## Seed survey numbers

| Survey No. | Owner | Mutation | Notes |
|---|---|---|---|
| 101 | ABC Industries Pvt Ltd | APPROVED | Clean record |
| 102 | ABC Industries Pvt Ltd | APPROVED | Clean record |
| 103 | ABC Industries Pvt Ltd | PENDING | Use this for the "pending → approved" polling demo |
| 104 | XYZ Textiles Ltd | REJECTED | Agricultural land |
| 105 | Konkan Ventures LLP | APPROVED | Blocked by encumbrance + court case |
| 999 | Demo Outage Corp | APPROVED | Always simulates a 503 outage |

## Example requests

### 1. Unauthorized access (401)
```bash
curl -i http://localhost:4000/api/land/status/101
```

### 2. Valid key, insufficient permission (403)
```bash
curl -i http://localhost:4000/api/land/records/101 \
  -H "X-API-Key: discom-demo-key-003"
```

### 3. Raw legacy record vs. canonical view
```bash
curl http://localhost:4000/api/land/records/102 \
  -H "X-API-Key: interop-demo-key-001"

curl "http://localhost:4000/api/land/records/102?schema=canonical" \
  -H "X-API-Key: interop-demo-key-001"
```

### 4. Verify a dependency (policy engine)
```bash
curl -X POST http://localhost:4000/api/land/verify \
  -H "X-API-Key: mpcb-demo-key-002" \
  -H "Content-Type: application/json" \
  -d '{"surveyNumber": "102", "pan": "ABCDE1234F"}'
```

### 5. The "pending mutation" scenario (Section 9)
```bash
# Step 1 — check status, see WAITING behavior
curl -X POST http://localhost:4000/api/land/verify \
  -H "X-API-Key: mpcb-demo-key-002" -H "Content-Type: application/json" \
  -d '{"surveyNumber": "103", "pan": "ABCDE1234F"}'
# -> dependency_status: "WAITING"

# Step 2 — simulate the Land Department approving the mutation
curl -X PATCH http://localhost:4000/api/land/records/103/mutation \
  -H "X-API-Key: interop-demo-key-001" -H "Content-Type: application/json" \
  -d '{"mutation_status": "APPROVED"}'

# Step 3 — re-check, dependency now resolves
curl -X POST http://localhost:4000/api/land/verify \
  -H "X-API-Key: mpcb-demo-key-002" -H "Content-Type: application/json" \
  -d '{"surveyNumber": "103", "pan": "ABCDE1234F"}'
# -> dependency_status: "RESOLVED"
```

### 6. Schema drift detection (Section 11)
```bash
curl -X POST http://localhost:4000/api/land/schema-mapping/detect \
  -H "X-API-Key: interop-demo-key-001" -H "Content-Type: application/json" \
  -d '{"survey_no": "102", "owner_name": "ABC Industries Pvt Ltd", "mutation": "APPROVED"}'
```

### 7. Fault tolerance / retry demo (Section 12)
```bash
# Survey 999 always simulates an outage
curl -i http://localhost:4000/api/land/status/999 \
  -H "X-API-Key: interop-demo-key-001"

# Or force it on any record with a header or query param
curl -i "http://localhost:4000/api/land/status/101?simulateFailure=true" \
  -H "X-API-Key: interop-demo-key-001"
```

### 8. Audit trail (Section 13)
```bash
curl http://localhost:4000/api/land/audit \
  -H "X-API-Key: interop-demo-key-001"
```

## What this service deliberately does NOT do

- Store real government data or credentials
- Make cross-department eligibility decisions (that's the interoperability
  layer's policy engine, calling this API as one input)
- Persist mutation-status changes beyond the running process (in-memory only)

## Project structure

```
land-department-api/
├── server.js                  # entry point
├── config/consumers.js        # API keys + permissions
├── middleware/
│   ├── auth.js                # 401/403 enforcement
│   └── errorHandler.js
├── routes/land.js             # all /api/land/* endpoints
├── utils/
│   ├── schemaMapper.js        # canonical mapping + drift detection
│   ├── policyEngine.js        # deterministic dependency checks
│   ├── audit.js                # transaction logging
│   └── failureSimulator.js    # controlled 503s for retry demos
└── data/
    ├── landRecords.json       # seed data (legacy schema)
    └── store.js                # in-memory lookup/update
```
