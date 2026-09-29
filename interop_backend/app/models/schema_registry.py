import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class SchemaMappingRule(Base):
    __tablename__ = "schema_mapping_rules"

    id = Column(Integer, primary_key=True, index=True)
    department_code = Column(String(50), index=True, nullable=False)  # LAND, ELECTRICITY, POLLUTION
    source_field = Column(String(100), nullable=False)
    target_canonical_field = Column(String(100), nullable=False)
    rule_type = Column(String(50), default="DIRECT", nullable=False)  # DIRECT, LOOKUP, TRANSFORM, COMPUTED
    transformation_expression = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)


class SchemaDriftLog(Base):
    __tablename__ = "schema_drift_logs"

    id = Column(Integer, primary_key=True, index=True)
    department_code = Column(String(50), index=True, nullable=False)
    detected_field = Column(String(100), nullable=False)
    suggested_canonical_field = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=False)
    status = Column(String(50), default="PENDING_APPROVAL", nullable=False)  # PENDING_APPROVAL, APPROVED, REJECTED
    detected_at = Column(DateTime, default=get_utc_now)
    approved_at = Column(DateTime, nullable=True)
