from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LandDetails(BaseModel):
    survey_number: Optional[str] = None
    area: Optional[float] = None
    area_unit: Optional[str] = None
    land_type: Optional[str] = None
    mutation_status: Optional[str] = None  # APPROVED, PENDING, REJECTED
    ownership_status: Optional[str] = None  # VALID, INVALID, UNKNOWN
    encumbrance: Optional[bool] = None
    court_case: Optional[bool] = None


class ElectricityDetails(BaseModel):
    application_number: Optional[str] = None
    consumer_number: Optional[str] = None
    requested_load_kw: Optional[float] = None
    sanctioned_load_kw: Optional[float] = None
    supply_category: Optional[str] = None
    connection_type: Optional[str] = None
    application_status: Optional[str] = None
    inspection_status: Optional[str] = None
    meter_status: Optional[str] = None
    connection_status: Optional[str] = None
    outstanding_dues: Optional[bool] = None
    security_deposit: Optional[str] = None


class PollutionDetails(BaseModel):
    application_no: Optional[str] = None
    project_id: Optional[str] = None
    consent_type: Optional[str] = None  # CTE, CTO
    consent_status: Optional[str] = None  # APPROVED, PENDING, REJECTED
    valid_until: Optional[str] = None
    compliance_status: Optional[str] = None  # COMPLIANT, NON_COMPLIANT
    air_emission_category: Optional[str] = None
    water_discharge_category: Optional[str] = None
    hazardous_waste: Optional[bool] = None
    environmental_clearance_required: Optional[bool] = None


class CanonicalProjectModel(BaseModel):
    organization_pan: str
    organization_name: str
    project_id: Optional[str] = None
    application_number: Optional[str] = None
    district: Optional[str] = None
    location: Optional[str] = None
    industry_type: Optional[str] = None
    status: str = "WAITING"  # RESOLVED, WAITING, ACTION_REQUIRED, FAILED

    land_details: Optional[LandDetails] = None
    electricity_details: Optional[ElectricityDetails] = None
    pollution_details: Optional[PollutionDetails] = None


class TransformRequest(BaseModel):
    department: str = Field(..., json_schema_extra={"example": "ELECTRICITY"})
    raw_payload: Dict[str, Any]
    requested_pan: Optional[str] = Field(None, json_schema_extra={"example": "ABCDE1234F"})
