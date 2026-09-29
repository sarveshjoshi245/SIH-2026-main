from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    OtpRequestBody,
    OtpVerifyRequest,
    OtpRequestResponse,
    TokenResponse,
    UserProfileResponse,
)
from app.auth.jwt_handler import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.auth.otp_store import generate_otp, verify_otp

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])


def _mask_aadhaar(aadhaar: str) -> str:
    return f"XXXX-XXXX-{aadhaar[-4:]}"


# ---------------------------------------------------------------------------
# REGISTER
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register User",
    description="""
Register a new user account.

**Required**: `organization_name`, `organization_pan`, `aadhaar_number`  
**Optional**: `email`, `password` (enables classic email+password login in addition to OTP)

After registration, login via Aadhaar/PAN + OTP, or email + password if provided.
"""
)
def register_user(body: UserRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.organization_pan == body.organization_pan.upper()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "ERROR", "message": f"An account with PAN {body.organization_pan.upper()} already exists"}
        )
    if db.query(User).filter(User.aadhaar_number == body.aadhaar_number).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "ERROR", "message": "An account with this Aadhaar number already exists"}
        )
    if body.email and db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "ERROR", "message": "An account with this email already exists"}
        )

    new_user = User(
        email=body.email,
        hashed_password=hash_password(body.password) if body.password else None,
        organization_name=body.organization_name,
        organization_pan=body.organization_pan.strip().upper(),
        aadhaar_number=body.aadhaar_number,
        aadhaar_masked=_mask_aadhaar(body.aadhaar_number),
        is_aadhaar_verified=True,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------------
# OTP — Request
# ---------------------------------------------------------------------------

@router.post(
    "/otp/request",
    response_model=OtpRequestResponse,
    summary="Request OTP (Aadhaar / PAN Login)",
    description="""
Send an OTP for login using either Aadhaar or PAN.

- `login_method`: `AADHAAR` or `PAN`
- `identifier`: 12-digit Aadhaar OR 10-char PAN

> **Demo**: OTP returned in `demo_otp`. Remove in production — send via SMS/DigiLocker.
"""
)
def request_otp(body: OtpRequestBody, db: Session = Depends(get_db)):
    if body.login_method == "AADHAAR":
        user = db.query(User).filter(User.aadhaar_number == body.identifier.strip()).first()
        hint = f"Aadhaar ending in ...{body.identifier[-4:]}"
    else:
        user = db.query(User).filter(User.organization_pan == body.identifier.strip().upper()).first()
        hint = f"PAN {body.identifier.strip().upper()}"

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "NOT_FOUND", "message": f"No registered user found for this {body.login_method}"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "FORBIDDEN", "message": "Account is inactive"}
        )

    otp = generate_otp(body.identifier, body.login_method)
    return OtpRequestResponse(
        status="OTP_SENT",
        message=f"A 6-digit OTP has been dispatched for {hint}. Valid for 5 minutes.",
        demo_otp=otp
    )


# ---------------------------------------------------------------------------
# OTP — Verify (Login)
# ---------------------------------------------------------------------------

@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    summary="Verify OTP and Login",
    description="Submit the 6-digit OTP to get a JWT access token."
)
def verify_otp_login(body: OtpVerifyRequest, db: Session = Depends(get_db)):
    if not verify_otp(body.identifier, body.login_method, body.otp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "UNAUTHORIZED", "message": "Invalid or expired OTP. Please request a new one."}
        )

    if body.login_method == "AADHAAR":
        user = db.query(User).filter(User.aadhaar_number == body.identifier.strip()).first()
    else:
        user = db.query(User).filter(User.organization_pan == body.identifier.strip().upper()).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "FORBIDDEN", "message": "Account not found or inactive"}
        )

    token = create_access_token({
        "sub": user.email or user.organization_pan,
        "pan": user.organization_pan,
        "org": user.organization_name,
        "login_method": body.login_method,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        organization_pan=user.organization_pan,
        organization_name=user.organization_name,
    )


# ---------------------------------------------------------------------------
# EMAIL/PASSWORD Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Email + Password Login",
    description="Login with email and password (only if provided during registration)."
)
def login_user(body: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "UNAUTHORIZED", "message": "Invalid email or password"}
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "FORBIDDEN", "message": "Account is inactive"}
        )

    token = create_access_token({
        "sub": user.email,
        "pan": user.organization_pan,
        "org": user.organization_name,
        "login_method": "EMAIL",
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        organization_pan=user.organization_pan,
        organization_name=user.organization_name,
    )


# ---------------------------------------------------------------------------
# PROFILE
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Current User Profile",
    description="Get your profile including masked Aadhaar."
)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
