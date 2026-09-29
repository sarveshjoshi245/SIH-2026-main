/**
 * Pollution Department native schema -> interoperability canonical model.
 * The native names intentionally differ from Land/Electricity.
 */
const KNOWN_MAPPING = {
  application_no: 'environment_application_number',
  application_project_id: 'project_id',
  industry_name: 'organization_name',
  industry_pan: 'organization_pan',
  plant_location: 'location',
  region: 'district',
  industry_type: 'industry_type',
  consent_type: 'consent_type',
  consent_status: 'consent_status',
  valid_until: 'consent_valid_until',
  compliance_status: 'compliance_status',
  air_emission_category: 'air_emission_category',
  water_discharge_category: 'water_discharge_category',
  hazardous_waste: 'hazardous_waste',
  environmental_clearance_required: 'environmental_clearance_required'
};

const ALIAS_TABLE = {
  application_id: { canonical: 'environment_application_number', confidence: 0.98 },
  project_reference: { canonical: 'project_id', confidence: 0.96 },
  project_ref: { canonical: 'project_id', confidence: 0.95 },
  company_name: { canonical: 'organization_name', confidence: 0.96 },
  organization: { canonical: 'organization_name', confidence: 0.9 },
  pan: { canonical: 'organization_pan', confidence: 0.95 },
  plant_address: { canonical: 'location', confidence: 0.94 },
  location: { canonical: 'location', confidence: 0.93 },
  district_name: { canonical: 'district', confidence: 0.95 },
  industry_category: { canonical: 'industry_type', confidence: 0.95 },
  consent: { canonical: 'consent_status', confidence: 0.94 },
  approval_status: { canonical: 'consent_status', confidence: 0.92 },
  consent_validity: { canonical: 'consent_valid_until', confidence: 0.93 },
  valid_to: { canonical: 'consent_valid_until', confidence: 0.9 },
  compliance: { canonical: 'compliance_status', confidence: 0.96 },
  waste_hazardous: { canonical: 'hazardous_waste', confidence: 0.92 }
};

function toCanonical(record) {
  const canonical = {};
  for (const [departmentField, value] of Object.entries(record)) {
    if (departmentField === 'simulateOutage') continue;
    const canonicalField = KNOWN_MAPPING[departmentField] || departmentField;
    canonical[canonicalField] = value;
  }
  return canonical;
}

function detectSchemaDrift(payload) {
  const knownNative = new Set(Object.keys(KNOWN_MAPPING));
  const knownCanonical = new Set(Object.values(KNOWN_MAPPING));
  const suggestions = [];
  const unmapped = [];

  for (const field of Object.keys(payload)) {
    if (knownNative.has(field) || knownCanonical.has(field)) continue;

    const alias = ALIAS_TABLE[field];
    if (alias) {
      suggestions.push({
        received_field: field,
        suggested_canonical_field: alias.canonical,
        confidence: alias.confidence,
        note: 'AI/heuristic suggestion only — requires human or policy validation before use.'
      });
    } else {
      unmapped.push(field);
    }
  }

  return {
    drift_detected: suggestions.length > 0,
    suggestions,
    unmapped_fields: unmapped
  };
}

module.exports = { KNOWN_MAPPING, ALIAS_TABLE, toCanonical, detectSchemaDrift };
