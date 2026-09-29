import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime.datetime
    transaction_id: Optional[str]
    actor_email: Optional[str]
    masked_pan: Optional[str]
    endpoint: str
    action: str
    outcome: str
    response_code: int
    response_time_ms: float
