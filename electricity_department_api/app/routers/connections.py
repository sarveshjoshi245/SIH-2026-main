import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.api_key import require_scope
from app.models.electricity import ApiConsumer
from app.services.electricity_service import ElectricityService
from app.services.audit_service import AuditService
from app.utils.transaction import generate_transaction_id

router = APIRouter(prefix="/api/electricity", tags=["Electricity Connections"])


@router.get(
    "/connections/{consumer_number}",
    response_model=Dict[str, Any],
    summary="Get Existing Electricity Connection",
    description="Retrieve existing consumer connection details using legacy departmental schema."
)
def get_connection(
    consumer_number: str,
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
    consumer: ApiConsumer = Depends(require_scope("/api/electricity/*")),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    transaction_id = getattr(request.state, "transaction_id", generate_transaction_id())

    conn = ElectricityService.get_connection_by_consumer_number(db, consumer_number)
    elapsed_ms = (time.time() - start_time) * 1000

    if not conn:
        AuditService.log_request(
            db=db,
            transaction_id=transaction_id,
            endpoint=f"/api/electricity/connections/{consumer_number}",
            response_code=404,
            response_time_ms=elapsed_ms,
            outcome="FAILED",
            consumer_id=consumer.consumer_id,
            failure_type="CONSUMER_NOT_FOUND"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "NOT_FOUND",
                "department": "ELECTRICITY_DISTRIBUTION",
                "message": "Electricity consumer connection not found",
                "consumer_number": consumer_number,
                "transaction_id": transaction_id
            }
        )

    legacy_data = ElectricityService.to_legacy_connection_dict(conn)

    AuditService.log_request(
        db=db,
        transaction_id=transaction_id,
        endpoint=f"/api/electricity/connections/{consumer_number}",
        response_code=200,
        response_time_ms=elapsed_ms,
        outcome="SUCCESS",
        consumer_id=consumer.consumer_id,
        application_number=conn.application_number
    )

    return legacy_data
