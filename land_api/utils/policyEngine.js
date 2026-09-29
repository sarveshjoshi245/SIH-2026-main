/**
 * Deterministic checks over a canonical land record. This is
 * intentionally simple and rule-based (Section 23: AI should not
 * make eligibility decisions) — it just states, in the open, which
 * facts were checked and why the dependency resolved the way it did.
 */
function evaluateLandDependency(canonicalRecord, expectedPan) {
  const checks = {
    pan_matches: Boolean(expectedPan) && canonicalRecord.organization_pan === expectedPan,
    mutation_approved: canonicalRecord.mutation_status === 'APPROVED',
    no_encumbrance: canonicalRecord.encumbrance === false,
    no_court_case: canonicalRecord.court_case === false
  };

  let dependencyStatus;
  if (!expectedPan || !checks.pan_matches) {
    dependencyStatus = 'FAILED';
  } else if (canonicalRecord.mutation_status === 'PENDING') {
    dependencyStatus = 'WAITING';
  } else if (['REJECTED', 'UNDER_OBJECTION'].includes(canonicalRecord.mutation_status)) {
    dependencyStatus = 'ACTION_REQUIRED';
  } else if (checks.mutation_approved && checks.no_encumbrance && checks.no_court_case) {
    dependencyStatus = 'RESOLVED';
  } else {
    dependencyStatus = 'ACTION_REQUIRED';
  }

  return { checks, dependency_status: dependencyStatus };
}

module.exports = { evaluateLandDependency };
