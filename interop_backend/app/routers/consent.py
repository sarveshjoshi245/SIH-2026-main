import json
import datetime
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.consent import UserConsent
from app.schemas.consent import ConsentGrantRequest, ConsentResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/consent", tags=["Consent Management"])


@router.post(
    "",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant Departmental Data Access Consent",
    description="Explicitly consent to allowing the interoperability platform to query designated departmental APIs."
)
def grant_consent(
    body: ConsentGrantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(days=body.expires_in_days) if body.expires_in_days else None

    # Deactivate older active consents for the same PAN if replacing
    existing = db.query(UserConsent).filter(
        UserConsent.organization_pan == current_user.organization_pan,
        UserConsent.is_active == True
    ).all()
    for c in existing:
        c.is_active = False

    new_consent = UserConsent(
        user_id=current_user.id,
        organization_pan=current_user.organization_pan,
        purpose=body.purpose,
        allowed_departments=json.dumps([d.upper() for d in body.allowed_departments]),
        is_active=True,
        granted_at=now,
        expires_at=expires
    )
    db.add(new_consent)
    db.commit()
    db.refresh(new_consent)
    return new_consent


@router.get(
    "/my",
    response_model=List[ConsentResponse],
    summary="Get Active Consents",
    description="Retrieve all consent records granted by the logged-in organization."
)
def get_my_consents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(UserConsent).filter(
        UserConsent.organization_pan == current_user.organization_pan
    ).order_by(UserConsent.id.desc()).all()
