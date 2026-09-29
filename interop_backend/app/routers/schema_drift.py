from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.schema_registry import SchemaMappingRule, SchemaDriftLog
from app.schemas.schema_drift import (
    DriftDetectionRequest,
    DriftSuggestionResponse,
    DriftApprovalRequest,
)
from app.engine.ai_drift_resolver import AIDriftResolver
from app.auth.dependencies import require_role

router = APIRouter(prefix="/api/schema", tags=["AI-Assisted Schema Drift"])


@router.post(
    "/detect",
    response_model=DriftSuggestionResponse,
    summary="Detect Schema Drift & Generate AI Suggestions",
    description="Analyze a departmental payload for unmapped field mutations and generate semantic mapping suggestions with confidence scores."
)
def detect_schema_drift(body: DriftDetectionRequest, db: Session = Depends(get_db)):
    result = AIDriftResolver.detect_and_suggest(body.department_code, body.sample_payload)

    # Record detected drifts in DB
    for suggestion in result.suggestions:
        existing = db.query(SchemaDriftLog).filter(
            SchemaDriftLog.department_code == body.department_code.upper(),
            SchemaDriftLog.detected_field == suggestion.detected_field
        ).first()
        if not existing:
            db.add(SchemaDriftLog(
                department_code=body.department_code.upper(),
                detected_field=suggestion.detected_field,
                suggested_canonical_field=suggestion.suggested_canonical_field,
                confidence_score=suggestion.confidence_score,
                status="PENDING_APPROVAL"
            ))
    db.commit()
    return result


@router.post(
    "/approve-drift",
    summary="Approve Schema Drift & Update Live Registry",
    description="Government administrator approves an AI-suggested mapping and dynamically registers it into the active schema mapper."
)
def approve_drift_mapping(
    body: DriftApprovalRequest,
    current_user: User = Depends(require_role(User.ROLE_ADMIN)),
    db: Session = Depends(get_db)
):
    # Update drift log
    log = db.query(SchemaDriftLog).filter(
        SchemaDriftLog.department_code == body.department_code.upper(),
        SchemaDriftLog.detected_field == body.source_field
    ).first()
    if log:
        log.status = "APPROVED"

    # Add active mapping rule
    new_rule = SchemaMappingRule(
        department_code=body.department_code.upper(),
        source_field=body.source_field,
        target_canonical_field=body.target_canonical_field,
        rule_type="DIRECT",
        is_active=True
    )
    db.add(new_rule)
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Successfully mapped '{body.source_field}' -> '{body.target_canonical_field}' for department {body.department_code.upper()}",
        "approved_by": current_user.email or current_user.organization_pan
    }
