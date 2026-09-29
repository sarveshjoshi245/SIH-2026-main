import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.electricity import AuditLog


class AuditService:
    @staticmethod
    def log_request(
        db: Session,
        transaction_id: str,
        endpoint: str,
        response_code: int,
        response_time_ms: float,
        outcome: str,
        consumer_id: Optional[str] = None,
        application_number: Optional[str] = None,
        failure_type: Optional[str] = None
    ) -> AuditLog:
        """Create a persistent departmental audit log entry."""
        audit_entry = AuditLog(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            transaction_id=transaction_id,
            consumer_id=consumer_id,
            endpoint=endpoint,
            application_number=application_number,
            outcome=outcome,
            response_code=response_code,
            response_time_ms=response_time_ms,
            failure_type=failure_type
        )
        db.add(audit_entry)
        try:
            db.commit()
            db.refresh(audit_entry)
        except Exception:
            db.rollback()
        return audit_entry

    @staticmethod
    def get_audit_logs(
        db: Session,
        limit: int = 50,
        application_number: Optional[str] = None
    ) -> List[AuditLog]:
        """Fetch audit logs ordered by newest first."""
        query = db.query(AuditLog)
        if application_number:
            query = query.filter(AuditLog.application_number == application_number)
        return query.order_by(AuditLog.id.desc()).limit(limit).all()
