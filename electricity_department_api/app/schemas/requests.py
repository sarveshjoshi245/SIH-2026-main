from typing import Optional
from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    application_number: str = Field(
        ...,
        json_schema_extra={"example": "ELEC-2026-00102"},
        description="Authoritative Electricity Application Number"
    )
    pan: str = Field(
        ...,
        json_schema_extra={"example": "FGHIJ5678K"},
        description="Applicant Permanent Account Number (PAN) to match against departmental records"
    )


class AdminStateTransitionRequest(BaseModel):
    application_number: str = Field(
        ...,
        json_schema_extra={"example": "ELEC-2026-00102"},
        description="Electricity Application Number to mutate"
    )
    application_status: Optional[str] = Field(
        None,
        json_schema_extra={"example": "APPROVED"},
        description="SUBMITTED | UNDER_SCRUTINY | PENDING | APPROVED | REJECTED | UNDER_INSPECTION"
    )
    inspection_status: Optional[str] = Field(
        None,
        json_schema_extra={"example": "COMPLETED"},
        description="NOT_REQUIRED | PENDING | IN_PROGRESS | COMPLETED | FAILED"
    )
    meter_status: Optional[str] = Field(
        None,
        json_schema_extra={"example": "INSTALLED"},
        description="NOT_INSTALLED | INSTALLATION_SCHEDULED | INSTALLED"
    )
    connection_status: Optional[str] = Field(
        None,
        json_schema_extra={"example": "ENERGIZED"},
        description="NOT_CONNECTED | READY_FOR_ENERGIZATION | ENERGIZED | DISCONNECTED"
    )
    rejection_reason: Optional[str] = Field(
        None,
        json_schema_extra={"example": "Electrical infrastructure inspection failed"}
    )
    outstanding_dues: Optional[bool] = Field(
        None,
        json_schema_extra={"example": False}
    )
    security_deposit_status: Optional[str] = Field(
        None,
        json_schema_extra={"example": "PAID"},
        description="PENDING | PAID | WAIVED | NOT_REQUIRED"
    )
