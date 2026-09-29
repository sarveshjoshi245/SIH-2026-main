from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
import re


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Register a new user with Aadhaar + PAN identity."""
    organization_name: str = Field(..., json_schema_extra={"example": "ABC Industries Pvt Ltd"})
    organization_pan: str = Field(..., json_schema_extra={"example": "ABCDE1234F"})
    aadhaar_number: str = Field(..., min_length=12, max_length=12, json_schema_extra={"example": "987654321012"})
    # Email & password are optional — user can choose OTP-only login later
    email: Optional[EmailStr] = Field(None, json_schema_extra={"example": "applicant@abcindustries.com"})
    password: Optional[str] = Field(None, min_length=6, json_schema_extra={"example": "SecretPass123"})

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Aadhaar number must contain only digits")
        return v

    @field_validator("organization_pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        pan_regex = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        if not re.match(pan_regex, v.strip().upper()):
            raise ValueError("Invalid PAN format (e.g. ABCDE1234F)")
        return v.strip().upper()


# ---------------------------------------------------------------------------
# OTP Request / Verify (for Aadhaar or PAN based login)
# ---------------------------------------------------------------------------

class OtpRequestBody(BaseModel):
    """Request an OTP to be sent for Aadhaar or PAN login."""
    login_method: Literal["AADHAAR", "PAN"] = Field(
        ...,
        json_schema_extra={"example": "AADHAAR"},
        description="Use 'AADHAAR' for Aadhaar-based OTP or 'PAN' for PAN-based OTP."
    )
    identifier: str = Field(
        ...,
        json_schema_extra={"example": "987654321012"},
        description="The 12-digit Aadhaar number OR the 10-character PAN depending on login_method."
    )


class OtpVerifyRequest(BaseModel):
    """Submit the OTP received to complete login and obtain JWT token."""
    login_method: Literal["AADHAAR", "PAN"] = Field(..., json_schema_extra={"example": "AADHAAR"})
    identifier: str = Field(..., json_schema_extra={"example": "987654321012"})
    otp: str = Field(..., min_length=6, max_length=6, json_schema_extra={"example": "452901"})


class OtpRequestResponse(BaseModel):
    """Response when OTP is dispatched."""
    status: str
    message: str
    # For demo only — in production this would be REMOVED and OTP sent via SMS/DigiLocker
    demo_otp: Optional[str] = None


# ---------------------------------------------------------------------------
# Classic Email/Password Login (still supported)
# ---------------------------------------------------------------------------

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., json_schema_extra={"example": "applicant@abcindustries.com"})
    password: str = Field(..., json_schema_extra={"example": "SecretPass123"})


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_pan: str
    organization_name: str


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: Optional[str]
    organization_name: str
    organization_pan: str
    aadhaar_masked: Optional[str]
    is_aadhaar_verified: bool
    is_active: bool
