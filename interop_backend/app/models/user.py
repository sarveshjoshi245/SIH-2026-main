import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    ROLE_APPLICANT = "APPLICANT"
    ROLE_ADMIN = "ADMIN"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)  # Optional when using Aadhaar/PAN login
    hashed_password = Column(String(255), nullable=True)  # Nullable when OTP-only login is used
    organization_name = Column(String(255), nullable=False)
    organization_pan = Column(String(20), unique=True, index=True, nullable=False)
    aadhaar_number = Column(String(12), unique=True, index=True, nullable=True)  # 12-digit Aadhaar
    aadhaar_masked = Column(String(20), nullable=True)  # Masked e.g. XXXX-XXXX-7890
    is_aadhaar_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(30), default=ROLE_APPLICANT, nullable=False)  # APPLICANT, ADMIN

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
