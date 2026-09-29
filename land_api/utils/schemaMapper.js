/**
 * The Land Department's native (legacy) field names, mapped to the
 * interoperability layer's canonical model. See Section 14 of the
 * project write-up.
 */
const KNOWN_MAPPING = {
  gtn: 'survey_number',
  malak_name: 'owner',
  malak_pan: 'organization_pan',
  kshetra: 'area_hectares',
  kshetra_unit: 'area_unit',
  jamabandi: 'mutation_status',
  jamin_prakar: 'land_type',
  bandhak: 'encumbrance',
  court_case: 'court_case',
  district: 'district',
  taluka: 'taluka',
  village: 'village'
};

/**
 * Fields we DON'T control ourselves that other legacy or successor
 * systems have been observed to use for the same concepts, plus a
 * confidence score. This is what lets the interoperability layer's
 * adapter flag "schema drift" instead of silently failing when a
 * department renames a field (Section 11).
 */
const ALIAS_TABLE = {
  survey_no: { canonical: 'survey_number', confidence: 0.98 },
  owner_name: { canonical: 'owner', confidence: 0.96 },
  registered_owner: { canonical: 'owner', confidence: 0.9 },
  pan: { canonical: 'organization_pan', confidence: 0.95 },
  owner_pan: { canonical: 'organization_pan', confidence: 0.93 },
  area: { canonical: 'area_hectares', confidence: 0.9 },
  area_ha: { canonical: 'area_hectares', confidence: 0.94 },
  mutation: { canonical: 'mutation_status', confidence: 0.97 },
  mutation_state: { canonical: 'mutation_status', confidence: 0.92 },
  land_category: { canonical: 'land_type', confidence: 0.95 },
  encumbered: { canonical: 'encumbrance', confidence: 0.93 },
  has_encumbrance: { canonical: 'encumbrance', confidence: 0.91 }
};

/** Converts a raw legacy-shaped record into the canonical model. */
function toCanonical(record) {
  const canonical = {};
  for (const [legacyField, value] of Object.entries(record)) {
    if (legacyField === 'simulateOutage') continue; // internal demo flag, not real data
    const canonicalField = KNOWN_MAPPING[legacyField] || legacyField;
    canonical[canonicalField] = value;
  }
  return canonical;
}

/**
 * Given an arbitrary payload (e.g. from a department that has
 * drifted to new field names), suggest canonical mappings for any
 * field we don't already recognize.
 */
function detectSchemaDrift(payload) {
  const knownLegacy = new Set(Object.keys(KNOWN_MAPPING));
  const knownCanonical = new Set(Object.values(KNOWN_MAPPING));
  const suggestions = [];
  const unmapped = [];

  for (const field of Object.keys(payload)) {
    if (knownLegacy.has(field) || knownCanonical.has(field)) continue;

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
