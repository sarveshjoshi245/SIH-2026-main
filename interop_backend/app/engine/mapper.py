from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.schemas.canonical import (
    CanonicalProjectModel,
    LandDetails,
    ElectricityDetails,
    PollutionDetails,
)
from app.models.schema_registry import SchemaMappingRule


def set_nested_value(target_dict: dict, path: str, value: Any):
    keys = path.split(".")
    current = target_dict
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


class RuleBasedMapper:
    """Deterministic, rule-based schema transformation engine."""

    # 1. LAND RULES
    LAND_DIRECT_MAP = {
        "gtn": "land_details.survey_number",
        "survey_no": "land_details.survey_number",
        "surveyNumber": "land_details.survey_number",
        "malak_name": "organization_name",
        "owner_name": "organization_name",
        "malak_pan": "organization_pan",
        "owner_pan": "organization_pan",
        "kshetra": "land_details.area",
        "area_hectares": "land_details.area",
        "kshetra_unit": "land_details.area_unit",
        "area_unit": "land_details.area_unit",
        "jamabandi": "land_details.mutation_status",
        "mutation_status": "land_details.mutation_status",
        "jamin_prakar": "land_details.land_type",
        "land_type": "land_details.land_type",
        "bandhak": "land_details.encumbrance",
        "encumbrance": "land_details.encumbrance",
        "court_case": "land_details.court_case",
        "district": "district",
    }

    # 2. ELECTRICITY RULES
    ELECTRICITY_DIRECT_MAP = {
        "appl_no": "electricity_details.application_number",
        "application_no": "electricity_details.application_number",
        "cons_no": "electricity_details.consumer_number",
        "cust_name": "organization_name",
        "consumer_name": "organization_name",
        "cust_pan": "organization_pan",
        "load_req": "electricity_details.requested_load_kw",
        "load_sanc": "electricity_details.sanctioned_load_kw",
        "sanctioned_load": "electricity_details.sanctioned_load_kw",
        "conn_type": "electricity_details.connection_type",
        "appl_stat": "electricity_details.application_status",
        "application_status": "electricity_details.application_status",
        "insp_stat": "electricity_details.inspection_status",
        "inspection_status": "electricity_details.inspection_status",
        "meter_stat": "electricity_details.meter_status",
        "meter_status": "electricity_details.meter_status",
        "conn_stat": "electricity_details.connection_status",
        "connection_status": "electricity_details.connection_status",
        "dues_flag": "electricity_details.outstanding_dues",
        "outstanding_dues_flag": "electricity_details.outstanding_dues",
        "sec_dep": "electricity_details.security_deposit",
        "security_deposit": "electricity_details.security_deposit",
    }

    CATEGORY_LOOKUP = {
        "HT-IND": "INDUSTRIAL",
        "LT-IND": "INDUSTRIAL",
        "HT-COM": "COMMERCIAL",
        "LT-COM": "COMMERCIAL",
        "AGR": "AGRICULTURAL",
    }

    # 3. POLLUTION RULES
    POLLUTION_DIRECT_MAP = {
        "application_no": "pollution_details.application_no",
        "environment_application_number": "pollution_details.application_no",
        "application_project_id": "project_id",
        "project_id": "project_id",
        "industry_name": "organization_name",
        "industry_pan": "organization_pan",
        "plant_location": "location",
        "region": "district",
        "industry_type": "industry_type",
        "consent_type": "pollution_details.consent_type",
        "consent_status": "pollution_details.consent_status",
        "valid_until": "pollution_details.valid_until",
        "compliance_status": "pollution_details.compliance_status",
        "air_emission_category": "pollution_details.air_emission_category",
        "water_discharge_category": "pollution_details.water_discharge_category",
        "hazardous_waste": "pollution_details.hazardous_waste",
        "environmental_clearance_required": "pollution_details.environmental_clearance_required",
    }

    @classmethod
    def _load_active_overrides(cls, db: Optional[Session], department_code: str) -> Dict[str, str]:
        """Approved SchemaMappingRule rows for this department, keyed by source field.

        These take priority over the static *_DIRECT_MAP dictionaries so a
        government admin can fix a renamed/unknown upstream field via the
        schema-drift approval flow without a code deploy. No db session (e.g.
        the ad-hoc /api/canonical/transform test endpoint) means static-only.
        """
        if db is None:
            return {}
        rules = db.query(SchemaMappingRule).filter(
            SchemaMappingRule.department_code == department_code,
            SchemaMappingRule.is_active == True,  # noqa: E712
        ).all()
        return {rule.source_field: rule.target_canonical_field for rule in rules}

    @classmethod
    def transform_land(
        cls,
        raw: Dict[str, Any],
        requested_pan: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CanonicalProjectModel:
        # Handle wrapped payload
        data = raw.get("canonical", raw)

        extracted: Dict[str, Any] = {
            "organization_pan": "",
            "organization_name": "",
            "land_details": {},
        }

        # DB-approved mappings win over the static dictionary for the same field.
        effective_map = {**cls.LAND_DIRECT_MAP, **cls._load_active_overrides(db, "LAND")}
        for source_k, target_path in effective_map.items():
            if source_k in data and data[source_k] is not None:
                val = data[source_k]
                if target_path == "land_details.area" and val is not None:
                    try:
                        val = float(val)
                    except (ValueError, TypeError):
                        pass
                if target_path in ["land_details.encumbrance", "land_details.court_case"]:
                    val = bool(val)
                set_nested_value(extracted, target_path, val)

        # Location concatenation
        taluka = data.get("taluka", "")
        village = data.get("village", "")
        if taluka or village:
            loc = f"{taluka}, {village}".strip().strip(",")
            extracted["location"] = loc

        # Ownership rule
        pan = extracted.get("organization_pan") or data.get("malak_pan", "")
        if requested_pan and pan:
            ownership_valid = pan.strip().upper() == requested_pan.strip().upper()
            extracted["land_details"]["ownership_status"] = "VALID" if ownership_valid else "INVALID"
        else:
            extracted["land_details"]["ownership_status"] = "UNKNOWN"

        # Status normalization
        jamabandi = data.get("jamabandi") or data.get("mutation_status")
        enc = extracted["land_details"].get("encumbrance", False)
        court = extracted["land_details"].get("court_case", False)
        if jamabandi == "APPROVED" and not enc and not court:
            extracted["status"] = "RESOLVED"
        elif jamabandi == "PENDING":
            extracted["status"] = "WAITING"
        else:
            extracted["status"] = "ACTION_REQUIRED"

        return CanonicalProjectModel(**extracted)

    @classmethod
    def transform_electricity(
        cls,
        raw: Dict[str, Any],
        requested_pan: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CanonicalProjectModel:
        # Handle wrapped verify responses e.g. { application: { ... } }
        data = raw.get("application", raw)

        extracted: Dict[str, Any] = {
            "organization_pan": "",
            "organization_name": "",
            "electricity_details": {},
        }

        effective_map = {**cls.ELECTRICITY_DIRECT_MAP, **cls._load_active_overrides(db, "ELECTRICITY")}
        for source_k, target_path in effective_map.items():
            if source_k in data and data[source_k] is not None:
                val = data[source_k]
                if target_path in ["electricity_details.requested_load_kw", "electricity_details.sanctioned_load_kw"]:
                    try:
                        val = float(val)
                    except (ValueError, TypeError):
                        pass
                if target_path == "electricity_details.outstanding_dues":
                    val = bool(val)
                set_nested_value(extracted, target_path, val)

        # Category Lookup
        cat = data.get("cat_code")
        if cat:
            extracted["industry_type"] = cls.CATEGORY_LOOKUP.get(cat, "OTHER")
            extracted["electricity_details"]["supply_category"] = cat

        # Status normalization
        appl_stat = data.get("appl_stat") or data.get("application_status")
        conn_stat = data.get("conn_stat") or data.get("connection_status")
        insp_stat = data.get("insp_stat") or data.get("inspection_status")
        dues = extracted["electricity_details"].get("outstanding_dues", False)

        if appl_stat == "APPROVED" and conn_stat == "ENERGIZED" and not dues:
            extracted["status"] = "RESOLVED"
        elif appl_stat in ["PENDING", "UNDER_SCRUTINY", "UNDER_INSPECTION"] or insp_stat == "IN_PROGRESS":
            extracted["status"] = "WAITING"
        else:
            extracted["status"] = "ACTION_REQUIRED"

        return CanonicalProjectModel(**extracted)

    @classmethod
    def transform_pollution(
        cls,
        raw: Dict[str, Any],
        requested_pan: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CanonicalProjectModel:
        data = raw.get("canonical", raw)

        extracted: Dict[str, Any] = {
            "organization_pan": "",
            "organization_name": "",
            "pollution_details": {},
        }

        effective_map = {**cls.POLLUTION_DIRECT_MAP, **cls._load_active_overrides(db, "POLLUTION")}
        for source_k, target_path in effective_map.items():
            if source_k in data and data[source_k] is not None:
                val = data[source_k]
                if target_path in ["pollution_details.hazardous_waste", "pollution_details.environmental_clearance_required"]:
                    val = bool(val)
                set_nested_value(extracted, target_path, val)

        # Status normalization
        consent = data.get("consent_status")
        compliance = data.get("compliance_status")

        if consent == "APPROVED" and compliance == "COMPLIANT":
            extracted["status"] = "RESOLVED"
        elif consent in ["PENDING", "UNDER_REVIEW"]:
            extracted["status"] = "WAITING"
        else:
            extracted["status"] = "ACTION_REQUIRED"

        return CanonicalProjectModel(**extracted)

    @classmethod
    def merge_to_unified_project(
        cls,
        project_name: str,
        land_canon: Optional[CanonicalProjectModel] = None,
        elec_canon: Optional[CanonicalProjectModel] = None,
        poll_canon: Optional[CanonicalProjectModel] = None,
    ) -> CanonicalProjectModel:
        """Merge fragments from the 3 departments into a single authoritative CanonicalProjectModel."""
        primary_pan = (
            (land_canon and land_canon.organization_pan) or
            (elec_canon and elec_canon.organization_pan) or
            (poll_canon and poll_canon.organization_pan) or
            "UNKNOWN"
        )
        primary_name = (
            (land_canon and land_canon.organization_name) or
            (elec_canon and elec_canon.organization_name) or
            (poll_canon and poll_canon.organization_name) or
            project_name
        )

        merged = CanonicalProjectModel(
            organization_pan=primary_pan,
            organization_name=primary_name,
            project_id=poll_canon.project_id if poll_canon else None,
            district=(land_canon and land_canon.district) or (poll_canon and poll_canon.district),
            location=(poll_canon and poll_canon.location) or (land_canon and land_canon.location),
            industry_type=(poll_canon and poll_canon.industry_type) or (elec_canon and elec_canon.industry_type),
            status="WAITING",
            land_details=land_canon.land_details if land_canon else None,
            electricity_details=elec_canon.electricity_details if elec_canon else None,
            pollution_details=poll_canon.pollution_details if poll_canon else None,
        )

        return merged
