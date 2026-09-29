import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.api_key import require_scope
from app.models.electricity import ApiConsumer
from app.services.electricity_service import ElectricityService
from app.services.audit_service import AuditService
from app.services.chaos_service import ChaosService
from app.utils.transaction import generate_transaction_id

router = APIRouter(prefix="/api/electricity", tags=["Electricity Applications"])


@router.get(
    "/applications/{application_number}",
    response_model=Dict[str, Any],
    summary="Get Raw Electricity Application",
    description="Retrieve authoritative departmental application facts in department-native legacy schema."
)
async def get_application(
    application_number: str,
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
    x_force_schema_drift: Optional[bool] = Header(False, alias="X-Force-Schema-Drift"),
    x_bypass_chaos: Optional[bool] = Header(False, alias="X-Bypass-Chaos"),
    consumer: ApiConsumer = Depends(require_scope("/api/electricity/*")),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    transaction_id = getattr(request.state, "transaction_id", generate_transaction_id())

    # Chaos check
    await ChaosService.maybe_simulate_chaos(
        endpoint_type="application",
        transaction_id=transaction_id,
        bypass=x_bypass_chaos
    )

    app = ElectricityService.get_application_by_number(db, application_number)
    elapsed_ms = (time.time() - start_time) * 1000

    if not app:
        AuditService.log_request(
            db=db,
            transaction_id=transaction_id,
            endpoint=f"/api/electricity/applications/{application_number}",
            response_code=404,
            response_time_ms=elapsed_ms,
            outcome="FAILED",
            consumer_id=consumer.consumer_id,
            application_number=application_number,
            failure_type="NOT_FOUND"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "NOT_FOUND",
                "department": "ELECTRICITY_DISTRIBUTION",
                "message": "Electricity application not found",
                "application_number": application_number,
                "transaction_id": transaction_id
            }
        )

    legacy_data = ElectricityService.to_legacy_application_dict(app)
    final_data = ChaosService.apply_schema_drift(legacy_data, force=x_force_schema_drift)

    AuditService.log_request(
        db=db,
        transaction_id=transaction_id,
        endpoint=f"/api/electricity/applications/{application_number}",
        response_code=200,
        response_time_ms=elapsed_ms,
        outcome="SUCCESS",
        consumer_id=consumer.consumer_id,
        application_number=application_number
    )

    return final_data
