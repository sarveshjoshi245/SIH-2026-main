from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DriftDetectionRequest(BaseModel):
    department_code: str = Field(..., json_schema_extra={"example": "ELECTRICITY"})
    sample_payload: Dict[str, Any] = Field(
        ...,
        json_schema_extra={"example": {"application_no": "ELEC-2026-00101", "approved_load": "500"}}
    )


class DriftSuggestion(BaseModel):
    detected_field: str
    suggested_canonical_field: str
    confidence_score: float
    rationale: str


class DriftSuggestionResponse(BaseModel):
    department_code: str
    has_drift: bool
    suggestions: List[DriftSuggestion]
    unmapped_fields: List[str]


class DriftApprovalRequest(BaseModel):
    department_code: str = Field(..., json_schema_extra={"example": "ELECTRICITY"})
    source_field: str = Field(..., json_schema_extra={"example": "approved_load"})
    target_canonical_field: str = Field(..., json_schema_extra={"example": "sanctioned_load_kw"})
