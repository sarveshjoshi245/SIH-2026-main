import time
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.api_key import require_scope
from app.models.electricity import ApiConsumer
from app.schemas.requests import VerifyRequest
from app.schemas.responses import VerifyResponse
from app.services.verification_service import VerificationService
from app.services.audit_service import AuditService
from app.services.chaos_service import ChaosService
from app.utils.transaction import generate_verify_transaction_id

router = APIRouter(prefix="/api/electricity", tags=["Verification"])


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify Electricity Application and Identity",
    description="Verify application facts and compare supplied PAN with departmental records."
)
async def verify_application(
    body: VerifyRequest,
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
    x_bypass_chaos: Optional[bool] = Header(False, alias="X-Bypass-Chaos"),
    consumer: ApiConsumer = Depends(require_scope("/api/electricity/*")),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    transaction_id = generate_verify_transaction_id()
    request.state.transaction_id = transaction_id

    # Chaos check
    await ChaosService.maybe_simulate_chaos(
        endpoint_type="verify",
        transaction_id=transaction_id,
        bypass=x_bypass_chaos
    )

    try:
        tid, pan_match, legacy_data, app = VerificationService.verify_application(
            db=db,
            application_number=body.application_number,
            pan=body.pan,
            transaction_id=transaction_id
        )
    except HTTPException as he:
        elapsed_ms = (time.time() - start_time) * 1000
        AuditService.log_request(
            db=db,
            transaction_id=transaction_id,
            endpoint="/api/electricity/verify",
            response_code=he.status_code,
            response_time_ms=elapsed_ms,
            outcome="FAILED",
            consumer_id=consumer.consumer_id,
            application_number=body.application_number,
            failure_type="NOT_FOUND" if he.status_code == 404 else "ERROR"
        )
        raise he

    elapsed_ms = (time.time() - start_time) * 1000

    AuditService.log_request(
        db=db,
        transaction_id=tid,
        endpoint="/api/electricity/verify",
        response_code=200,
        response_time_ms=elapsed_ms,
        outcome="SUCCESS" if pan_match else "PAN_MISMATCH",
        consumer_id=consumer.consumer_id,
        application_number=body.application_number,
        failure_type=None if pan_match else "PAN_MISMATCH"
    )

    return VerifyResponse(
        transaction_id=tid,
        status="SUCCESS",
        pan_match=pan_match,
        application=legacy_data,
        message="Departmental verification completed"
    )
