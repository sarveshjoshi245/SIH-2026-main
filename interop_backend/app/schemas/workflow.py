from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.canonical import CanonicalProjectModel


class PlantVerificationRequest(BaseModel):
    project_name: str = Field(..., json_schema_extra={"example": "Chakan Manufacturing Unit 2"})
    organization_pan: str = Field(..., json_schema_extra={"example": "ABCDE1234F"})
    land_survey_number: str = Field(..., json_schema_extra={"example": "101"})
    electricity_application_number: str = Field(..., json_schema_extra={"example": "ELEC-2026-00101"})
    pollution_application_number: str = Field(..., json_schema_extra={"example": "MPCB-8821"})
    industry_type: Optional[str] = Field("Chemical", json_schema_extra={"example": "Chemical"})


class DepartmentCheckResult(BaseModel):
    department: str
    status: str  # SUCCESS, FAILED, WAITING, ACTION_REQUIRED, UNAVAILABLE
    http_code: Optional[int] = None
    response_time_ms: float
    pan_match: bool
    summary: str
    raw_facts: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProjectVerificationResponse(BaseModel):
    transaction_id: str
    project_name: str
    organization_pan: str
    organization_name: str
    overall_clearance_status: str  # RESOLVED, WAITING, ACTION_REQUIRED, FAILED
    pan_identity_verified: bool
    department_checks: List[DepartmentCheckResult]
    canonical_project_state: CanonicalProjectModel
    recommended_next_action: str
