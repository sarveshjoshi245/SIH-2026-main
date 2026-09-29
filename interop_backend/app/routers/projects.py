import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.transaction import ProjectTransaction, DepartmentStepExecution
from app.schemas.workflow import PlantVerificationRequest, ProjectVerificationResponse
from app.auth.dependencies import get_current_user, check_consent_for_departments
from app.engine.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/api/projects", tags=["Plant Clearance Workflow"])
workflow_engine = WorkflowEngine()


@router.post(
    "/verify-plant",
    response_model=ProjectVerificationResponse,
    summary="Multi-Department Plant Verification",
    description="Orchestrates asynchronous calls to Land, Electricity, and Pollution APIs, normalizes heterogeneous schemas, checks PAN identity, and evaluates clearance status."
)
async def verify_plant_project(
    body: PlantVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Enforce active consent check for the 3 required departments
    check_consent_for_departments(
        db=db,
        user=current_user,
        required_departments=["LAND", "ELECTRICITY", "POLLUTION"]
    )

    # 2. Execute end-to-end workflow
    response = await workflow_engine.execute_plant_verification(
        db=db,
        request=body,
        user=current_user
    )

    return response


@router.get(
    "/transactions",
    response_model=List[Dict[str, Any]],
    summary="List Organization Transactions",
    description="Retrieve all clearance transactions initiated by the logged in organization."
)
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txns = db.query(ProjectTransaction).filter(
        ProjectTransaction.organization_pan == current_user.organization_pan
    ).order_by(ProjectTransaction.id.desc()).all()

    results = []
    for t in txns:
        results.append({
            "id": t.id,
            "transaction_id": t.transaction_id,
            "project_name": t.project_name,
            "organization_pan": t.organization_pan,
            "overall_status": t.overall_status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return results


@router.get(
    "/transactions/{transaction_id}",
    response_model=Dict[str, Any],
    summary="Get Detailed Transaction Execution",
    description="Retrieve full execution breakdown, canonical payload, and departmental step details for a transaction."
)
def get_transaction_detail(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txn = db.query(ProjectTransaction).filter(
        ProjectTransaction.transaction_id == transaction_id
    ).first()

    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "NOT_FOUND", "message": "Transaction not found"}
        )

    # Ensure PAN matches user's PAN
    if txn.organization_pan != current_user.organization_pan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "FORBIDDEN", "message": "Not authorized to view this transaction"}
        )

    steps = db.query(DepartmentStepExecution).filter(
        DepartmentStepExecution.transaction_id == transaction_id
    ).all()

    return {
        "transaction_id": txn.transaction_id,
        "project_name": txn.project_name,
        "organization_pan": txn.organization_pan,
        "organization_name": txn.organization_name,
        "overall_status": txn.overall_status,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "completed_at": txn.completed_at.isoformat() if txn.completed_at else None,
        "canonical_state": json.loads(txn.canonical_payload) if txn.canonical_payload else None,
        "department_executions": [
            {
                "department": s.department_code,
                "status": s.status,
                "http_status_code": s.http_status_code,
                "response_time_ms": s.response_time_ms,
                "error_message": s.error_message,
                "raw_response": json.loads(s.raw_response) if s.raw_response else None,
                "canonical_fragment": json.loads(s.canonical_fragment) if s.canonical_fragment else None,
                "executed_at": s.executed_at.isoformat() if s.executed_at else None
            }
            for s in steps
        ]
    }
