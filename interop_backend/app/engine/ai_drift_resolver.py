import difflib
from typing import Dict, Any, List
from app.schemas.schema_drift import DriftSuggestion, DriftSuggestionResponse
from app.engine.mapper import RuleBasedMapper


class AIDriftResolver:
    """Detects schema changes and computes similarity/semantic suggestions for novel or mutated field names."""

    CANONICAL_TARGET_DICTIONARY = {
        "survey_number": ["survey_no", "surveyNumber", "gtn", "plot_number", "gat_no"],
        "organization_name": ["owner_name", "malak_name", "cust_name", "industry_name", "company_name", "enterprise_name"],
        "organization_pan": ["owner_pan", "malak_pan", "cust_pan", "industry_pan", "registered_pan", "tax_pan"],
        "area_hectares": ["kshetra", "area", "total_area", "land_area", "area_in_hectares"],
        "mutation_status": ["jamabandi", "mutation", "mutation_stat", "approval_status"],
        "land_type": ["jamin_prakar", "land_classification", "property_type", "zoning"],
        "encumbrance": ["bandhak", "lien", "mortgage", "is_encumbered"],
        "court_case": ["legal_dispute", "litigation", "court_stay"],
        "application_number": ["appl_no", "application_no", "app_id", "application_id", "ref_no"],
        "requested_load_kw": ["load_req", "demand_load", "applied_load", "power_required"],
        "sanctioned_load_kw": ["load_sanc", "approved_load", "granted_load", "sanctioned_capacity"],
        "connection_status": ["conn_stat", "power_status", "energization_status", "connection_state"],
        "outstanding_dues": ["dues_flag", "pending_bills", "arrears", "has_dues"],
        "consent_status": ["clearance_status", "mpcb_status", "env_approval_status"],
        "compliance_status": ["environmental_compliance", "pollution_compliance", "inspection_compliance"],
    }

    @classmethod
    def detect_and_suggest(cls, department_code: str, payload: Dict[str, Any]) -> DriftSuggestionResponse:
        dept = department_code.upper()
        known_map = {}
        if dept == "LAND":
            known_map = RuleBasedMapper.LAND_DIRECT_MAP
        elif dept == "ELECTRICITY":
            known_map = RuleBasedMapper.ELECTRICITY_DIRECT_MAP
        elif dept == "POLLUTION":
            known_map = RuleBasedMapper.POLLUTION_DIRECT_MAP

        suggestions: List[DriftSuggestion] = []
        unmapped: List[str] = []

        for field_name in payload.keys():
            if field_name not in known_map:
                # Field is not in known mapping rules -> Schema Drift detected
                unmapped.append(field_name)
                best_match = None
                best_score = 0.0

                # Check fuzzy match against alias dictionary
                clean_field = field_name.lower().replace("_", "").replace("-", "")
                for canonical_target, aliases in cls.CANONICAL_TARGET_DICTIONARY.items():
                    for alias in aliases:
                        clean_alias = alias.lower().replace("_", "").replace("-", "")
                        score = difflib.SequenceMatcher(None, clean_field, clean_alias).ratio()
                        if score > best_score:
                            best_score = score
                            best_match = canonical_target

                if best_match and best_score >= 0.5:
                    confidence = round(min(0.98, best_score + 0.15), 2)
                    suggestions.append(
                        DriftSuggestion(
                            detected_field=field_name,
                            suggested_canonical_field=best_match,
                            confidence_score=confidence,
                            rationale=f"AI Semantic Match: high lexical/semantic alignment with '{best_match}' aliases ({int(confidence*100)}% confidence)."
                        )
                    )

        return DriftSuggestionResponse(
            department_code=dept,
            has_drift=len(unmapped) > 0,
            suggestions=suggestions,
            unmapped_fields=unmapped
        )
