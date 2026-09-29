import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class PlatformAuditLog(Base):
    __tablename__ = "platform_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=get_utc_now, index=True)
    transaction_id = Column(String(100), index=True, nullable=True)
    actor_email = Column(String(255), nullable=True)
    masked_pan = Column(String(20), nullable=True)
    endpoint = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)  # VERIFY_PLANT, SCHEMA_MAPPING_UPDATE, CONSENT_GRANTED
    outcome = Column(String(50), nullable=False)  # SUCCESS, FAILED, FORBIDDEN
    response_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
