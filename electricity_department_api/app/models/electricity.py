import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    Text,
)
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class ElectricityApplication(Base):
    __tablename__ = "electricity_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(50), unique=True, index=True, nullable=False)
    consumer_number = Column(String(50), nullable=True, index=True)
    applicant_name = Column(String(255), nullable=False)
    applicant_pan = Column(String(20), nullable=False, index=True)
    premises_address = Column(Text, nullable=False)
    district = Column(String(100), nullable=False)
    taluka = Column(String(100), nullable=False)
    village = Column(String(100), nullable=False)

    supply_category = Column(String(50), nullable=False)  # e.g., HT-IND, LT-IND
    connection_type = Column(String(50), nullable=False)  # e.g., INDUSTRIAL, COMMERCIAL
    requested_load = Column(String(50), nullable=False)   # e.g., "500"
    requested_load_unit = Column(String(20), nullable=False, default="KW")
    sanctioned_load = Column(String(50), nullable=False)  # e.g., "500"
    sanctioned_load_unit = Column(String(20), nullable=False, default="KW")

    # Native Statuses
    application_status = Column(String(50), nullable=False, default="PENDING")
    inspection_status = Column(String(50), nullable=False, default="PENDING")
    meter_status = Column(String(50), nullable=False, default="NOT_INSTALLED")
    connection_status = Column(String(50), nullable=False, default="NOT_CONNECTED")

    outstanding_dues = Column(Boolean, nullable=False, default=False)
    security_deposit_status = Column(String(50), nullable=False, default="PENDING")

    application_date = Column(DateTime, default=get_utc_now)
    last_updated = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    rejection_reason = Column(Text, nullable=True)
    objection_reason = Column(Text, nullable=True)
    inspection_reference = Column(String(100), nullable=True)


class ElectricityConnection(Base):
    __tablename__ = "electricity_connections"

    id = Column(Integer, primary_key=True, index=True)
    consumer_number = Column(String(50), unique=True, index=True, nullable=False)
    application_number = Column(String(50), nullable=True, index=True)
    applicant_name = Column(String(255), nullable=False)
    applicant_pan = Column(String(20), nullable=False, index=True)
    premises_address = Column(Text, nullable=False)
    supply_category = Column(String(50), nullable=False)
    connection_type = Column(String(50), nullable=False)
    sanctioned_load = Column(String(50), nullable=False)
    sanctioned_load_unit = Column(String(20), nullable=False, default="KW")
    meter_number = Column(String(50), nullable=True)
    meter_status = Column(String(50), nullable=False, default="INSTALLED")
    connection_status = Column(String(50), nullable=False, default="ENERGIZED")
    outstanding_dues = Column(Boolean, nullable=False, default=False)
    energization_date = Column(DateTime, default=get_utc_now)
    last_updated = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


class ApiConsumer(Base):
    __tablename__ = "api_consumers"

    id = Column(Integer, primary_key=True, index=True)
    consumer_id = Column(String(100), unique=True, index=True, nullable=False)
    api_key = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    allowed_scopes = Column(Text, nullable=False)  # JSON or comma-separated list of scopes
    created_at = Column(DateTime, default=get_utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=get_utc_now, index=True)
    transaction_id = Column(String(100), nullable=False, index=True)
    consumer_id = Column(String(100), nullable=True)
    endpoint = Column(String(255), nullable=False)
    application_number = Column(String(100), nullable=True)
    outcome = Column(String(50), nullable=False)  # SUCCESS, FAILED, UNAVAILABLE
    response_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    failure_type = Column(String(100), nullable=True)
