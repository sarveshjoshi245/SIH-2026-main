import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class ProjectTransaction(Base):
    __tablename__ = "project_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    organization_pan = Column(String(20), index=True, nullable=False)
    organization_name = Column(String(255), nullable=False)
    overall_status = Column(String(50), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, RESOLVED, WAITING, ACTION_REQUIRED, FAILED
    canonical_payload = Column(Text, nullable=True)  # JSON payload of merged canonical state
    created_at = Column(DateTime, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)


class DepartmentStepExecution(Base):
    __tablename__ = "department_step_executions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(100), index=True, nullable=False)
    department_code = Column(String(50), nullable=False)  # LAND, ELECTRICITY, POLLUTION
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED, TIMEOUT, CIRCUIT_OPEN
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=False)
    raw_response = Column(Text, nullable=True)
    canonical_fragment = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=get_utc_now)
