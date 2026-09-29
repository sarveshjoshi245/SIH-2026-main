# Pollution / Environment Department API (Simulated)

A simulated departmental API for the SIH Government Interoperability Layer.
It follows the same engineering pattern as the Land Department API while
using a deliberately different Pollution/Environment schema.

## Purpose

The API represents an independently owned environmental department system
that stores industrial consent and compliance information. It is NOT a real
MPCB/central-government integration and contains only synthetic demo data.

## Stack

- Node.js
- Express
- Morgan
- In-memory JSON datastore

## Port

```bash
npm install
npm start
```

Default: `http://localhost:4002`

## Authentication

Protected endpoints require:

```http
X-API-Key: interop-demo-key-001
```

Read-only key:

```http
X-API-Key: interop-readonly-key-001
```

## Native Pollution Schema

The service intentionally uses names different from the canonical model:

```json
{
  "application_no": "MPCB-8821",
  "application_project_id": "PROJ-102",
  "industry_name": "ABC Industries Pvt Ltd",
  "industry_pan": "ABCDE1234F",
  "plant_location": "MIDC Pune",
  "region": "Pune",
  "industry_type": "Chemical",
  "consent_type": "CTE",
  "consent_status": "APPROVED",
  "valid_until": "2027-03-31",
  "compliance_status": "COMPLIANT",
  "air_emission_category": "RED",
  "water_discharge_category": "HIGH",
  "hazardous_waste": true,
  "environmental_clearance_required": false
}
```

The interoperability adapter can normalize these into:

```text
application_no       -> environment_application_number
application_project_id -> project_id
industry_name        -> organization_name
industry_pan        -> organization_pan
plant_location       -> location
region               -> district
valid_until          -> consent_valid_until
```

## Endpoints

### Get application

```bash
curl -H "X-API-Key: interop-demo-key-001" \
  http://localhost:4002/api/pollution/applications/MPCB-8821
```

Canonical preview:

```bash
curl -H "X-API-Key: interop-demo-key-001" \
  "http://localhost:4002/api/pollution/applications/MPCB-8821?schema=canonical"
```

### Get status

```bash
curl -H "X-API-Key: interop-demo-key-001" \
  http://localhost:4002/api/pollution/status/MPCB-8821
```

### Verify

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: interop-demo-key-001" \
  -d '{"applicationNo":"MPCB-8821","pan":"ABCDE1234F","industryType":"Chemical"}' \
  http://localhost:4002/api/pollution/verify
```

### Demonstrate WAITING -> RESOLVED

Start with `MPCB-8822`, which has `PENDING` consent:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: interop-demo-key-001" \
  -d '{"applicationNo":"MPCB-8822","pan":"ABCDE1234F","industryType":"Chemical"}' \
  http://localhost:4002/api/pollution/verify
```

Advance the simulated department state:

```bash
curl -X PATCH \
  -H "Content-Type: application/json" \
  -H "X-API-Key: interop-demo-key-001" \
  -d '{"consent_status":"APPROVED"}' \
  http://localhost:4002/api/pollution/applications/MPCB-8822/consent
```

Verify again. The dependency can now resolve if the deterministic checks pass.

## Failure simulation

Application `MPCB-8999` is configured as a simulated outage record.

You can also force an outage:

```bash
curl -H "X-API-Key: interop-demo-key-001" \
  -H "X-Simulate-Failure: true" \
  http://localhost:4002/api/pollution/applications/MPCB-8821
```

The endpoint returns `503 Service Unavailable` with `Retry-After: 5`.

## Schema drift demo

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: interop-demo-key-001" \
  -d '{"application_id":"MPCB-8821","company_name":"ABC Industries","approval_status":"APPROVED","compliance":"COMPLIANT"}' \
  http://localhost:4002/api/pollution/schema-mapping/detect
```

The service returns suggestions with confidence scores. Suggestions are not
silently applied.

## Design boundary

This service is the Pollution department simulator. It should remain separate
from the main interoperability platform. The platform owns the canonical
model, cross-department workflow, consent/policy orchestration, project state,
and next-action logic.
