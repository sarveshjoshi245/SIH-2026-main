import time
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.api_key import require_scope
from app.models.electricity import ApiConsumer
from app.schemas.requests import AdminStateTransitionRequest
from app.schemas.responses import AdminStateTransitionResponse
from app.services.electricity_service import ElectricityService
from app.services.audit_service import AuditService
from app.utils.transaction import generate_transaction_id

router = APIRouter(prefix="/api/admin", tags=["Admin Demo"])


@router.post(
    "/set-state",
    response_model=AdminStateTransitionResponse,
    summary="DEMO ONLY: Mutate Departmental State",
    description="Dedicated administrative endpoint for hackathon demo orchestration to simulate asynchronous departmental approvals and inspections."
)
def admin_set_state(
    body: AdminStateTransitionRequest,
    request: Request,
    consumer: ApiConsumer = Depends(require_scope("/api/admin/*")),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    transaction_id = getattr(request.state, "transaction_id", generate_transaction_id("ELEC-ADMIN"))

    updated_app = ElectricityService.update_application_state(db, body)
    elapsed_ms = (time.time() - start_time) * 1000

    legacy_snapshot = ElectricityService.to_legacy_application_dict(updated_app)

    AuditService.log_request(
        db=db,
        transaction_id=transaction_id,
        endpoint="/api/admin/set-state",
        response_code=200,
        response_time_ms=elapsed_ms,
        outcome="ADMIN_MUTATION_SUCCESS",
        consumer_id=consumer.consumer_id,
        application_number=body.application_number
    )

    return AdminStateTransitionResponse(
        status="SUCCESS",
        message="Application state mutated successfully (DEMO / ADMIN ONLY)",
        application_number=body.application_number,
        updated_state=legacy_snapshot
    )
