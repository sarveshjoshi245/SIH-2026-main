import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    organization_pan = Column(String(20), index=True, nullable=False)
    purpose = Column(String(255), nullable=False)  # e.g., "Industrial Plant Establishment Clearance"
    allowed_departments = Column(Text, nullable=False)  # JSON list e.g. ["LAND", "ELECTRICITY", "POLLUTION"]
    is_active = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime, default=get_utc_now)
    expires_at = Column(DateTime, nullable=True)
