import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ConsentGrantRequest(BaseModel):
    purpose: str = Field(..., json_schema_extra={"example": "Industrial Manufacturing Plant Establishment Clearance"})
    allowed_departments: List[str] = Field(
        ...,
        json_schema_extra={"example": ["LAND", "ELECTRICITY", "POLLUTION"]},
        description="Departments permitted to be queried on behalf of applicant"
    )
    expires_in_days: Optional[int] = Field(365, json_schema_extra={"example": 365})


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_pan: str
    purpose: str
    allowed_departments: str
    is_active: bool
    granted_at: datetime.datetime
    expires_at: Optional[datetime.datetime]
