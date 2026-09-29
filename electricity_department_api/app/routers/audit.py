from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.api_key import require_scope
from app.models.electricity import ApiConsumer
from app.schemas.responses import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api", tags=["Audit"])


@router.get(
    "/audit",
    response_model=List[AuditLogResponse],
    summary="Department Audit Trail",
    description="Retrieve departmental API access logs, latencies, transaction IDs, and outcomes."
)
def get_audit_trail(
    limit: int = Query(50, ge=1, le=500, description="Max audit records to return"),
    application_number: Optional[str] = Query(None, description="Filter by application number"),
    consumer: ApiConsumer = Depends(require_scope("/api/audit")),
    db: Session = Depends(get_db),
):
    return AuditService.get_audit_logs(
        db=db,
        limit=limit,
        application_number=application_number
    )
