from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.electricity import ElectricityApplication
from app.services.electricity_service import ElectricityService
from app.services.chaos_service import ChaosService
from app.utils.transaction import generate_verify_transaction_id


class VerificationService:

    @staticmethod
    def verify_application(
        db: Session,
        application_number: str,
        pan: str,
        transaction_id: str | None = None
    ) -> Tuple[str, bool, Dict[str, Any] | None, ElectricityApplication | None]:
        """Verify application and PAN against departmental records.
        
        Returns:
            (transaction_id, pan_match, legacy_application_data, application_model)
        """
        tid = transaction_id or generate_verify_transaction_id()

        app = ElectricityService.get_application_by_number(db, application_number)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "NOT_FOUND",
                    "department": "ELECTRICITY_DISTRIBUTION",
                    "message": "Electricity application not found",
                    "application_number": application_number,
                    "transaction_id": tid
                }
            )

        # Check PAN match (case-insensitive)
        pan_match = (pan.strip().upper() == app.applicant_pan.strip().upper())

        # Build departmental legacy facts
        legacy_data = ElectricityService.to_legacy_application_dict(app)
        
        # Apply schema drift if configured
        final_data = ChaosService.apply_schema_drift(legacy_data)

        return tid, pan_match, final_data, app
