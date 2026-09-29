/**
 * Deterministic environmental verification rules.
 * AI is deliberately not used for eligibility decisions.
 */
function evaluatePollutionDependency(canonicalRecord, expectedPan, expectedIndustryType) {
  const now = new Date();
  const validUntil = canonicalRecord.consent_valid_until
    ? new Date(canonicalRecord.consent_valid_until + 'T23:59:59Z')
    : null;

  const checks = {
    pan_matches: Boolean(expectedPan) && canonicalRecord.organization_pan === expectedPan,
    industry_type_matches:
      Boolean(expectedIndustryType) && canonicalRecord.industry_type === expectedIndustryType,
    consent_approved: canonicalRecord.consent_status === 'APPROVED',
    consent_valid: Boolean(validUntil) && validUntil >= now,
    industry_compliant: canonicalRecord.compliance_status === 'COMPLIANT',
    environmental_clearance_satisfied: canonicalRecord.environmental_clearance_required === false
  };

  let dependencyStatus;

  if (!expectedPan || !checks.pan_matches) {
    dependencyStatus = 'FAILED';
  } else if (canonicalRecord.consent_status === 'PENDING') {
    dependencyStatus = 'WAITING';
  } else if (['REJECTED', 'UNDER_OBJECTION'].includes(canonicalRecord.consent_status)) {
    dependencyStatus = 'ACTION_REQUIRED';
  } else if (
    checks.industry_type_matches &&
    checks.consent_approved &&
    checks.consent_valid &&
    checks.industry_compliant &&
    checks.environmental_clearance_satisfied
  ) {
    dependencyStatus = 'RESOLVED';
  } else {
    dependencyStatus = 'ACTION_REQUIRED';
  }

  return { checks, dependency_status: dependencyStatus };
}

module.exports = { evaluatePollutionDependency };
