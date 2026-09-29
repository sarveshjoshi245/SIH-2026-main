import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base


def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # LAND, ELECTRICITY, POLLUTION
    name = Column(String(255), nullable=False)
    base_url = Column(String(255), nullable=False)
    auth_header_name = Column(String(50), default="X-API-Key", nullable=False)
    auth_token = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
