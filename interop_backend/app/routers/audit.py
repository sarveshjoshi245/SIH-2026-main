from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.audit import PlatformAuditLog
from app.schemas.audit import AuditLogResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/audit", tags=["Platform Audit Logging"])


@router.get(
    "",
    response_model=List[AuditLogResponse],
    summary="Retrieve Platform Audit Trail",
    description="Retrieve tamper-evident, masked access logs across all project clearance workflows."
)
def get_audit_trail(
    limit: int = Query(50, ge=1, le=500),
    transaction_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(PlatformAuditLog)
    # Filter logs to only the current authenticated user's actions
    user_identifier = current_user.email or current_user.organization_pan
    query = query.filter(PlatformAuditLog.actor_email == user_identifier)
    if transaction_id:
        query = query.filter(PlatformAuditLog.transaction_id == transaction_id)

    return query.order_by(PlatformAuditLog.id.desc()).limit(limit).all()
