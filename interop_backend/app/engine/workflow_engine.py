import uuid
import json
import datetime
import asyncio
from typing import Optional
from sqlalchemy.orm import Session

from app.models.transaction import ProjectTransaction, DepartmentStepExecution
from app.models.audit import PlatformAuditLog
from app.models.user import User
from app.schemas.workflow import (
    PlantVerificationRequest,
    ProjectVerificationResponse,
    DepartmentCheckResult,
)
from app.adapters.land_adapter import LandAdapter
from app.adapters.electricity_adapter import ElectricityAdapter
from app.adapters.pollution_adapter import PollutionAdapter
from app.engine.mapper import RuleBasedMapper
from app.engine.policy_engine import PolicyEngine
from app.utils.masking import mask_pan
from app.intake.dependency_resolver import resolve_execution_order

# Services dispatched by this workflow, named per the shared dependency
# resolver (app/intake/dependency_resolver.py) so execution order comes from
# that generic resolver instead of being hardcoded here.
PLANT_VERIFICATION_SERVICES = ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"]

# Departments that must be approved before Pollution is dispatched.
POLLUTION_DEPENDENCIES = ["LAND", "ELECTRICITY"]


def generate_transaction_id() -> str:
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    unique_token = uuid.uuid4().hex[:6].upper()
    return f"TXN-{today_str}-{unique_token}"


class WorkflowEngine:
    """Coordinates multi-department asynchronous querying, transformation, and policy evaluation."""

    def __init__(
        self,
        land_adapter: Optional[LandAdapter] = None,
        elec_adapter: Optional[ElectricityAdapter] = None,
        poll_adapter: Optional[PollutionAdapter] = None,
    ):
        self.land_adapter = land_adapter or LandAdapter()
        self.elec_adapter = elec_adapter or ElectricityAdapter()
        self.poll_adapter = poll_adapter or PollutionAdapter()

    async def execute_plant_verification(
        self,
        db: Session,
        request: PlantVerificationRequest,
        user: User,
        transaction_id: Optional[str] = None,
    ) -> ProjectVerificationResponse:
        txn_id = transaction_id or generate_transaction_id()
        start_time = datetime.datetime.now(datetime.timezone.utc)

        # 1. Create Initial Transaction Record
        txn_record = ProjectTransaction(
            transaction_id=txn_id,
            project_name=request.project_name,
            organization_pan=request.organization_pan,
            organization_name=user.organization_name,
            overall_status="IN_PROGRESS",
            canonical_payload=None,
        )
        db.add(txn_record)
        db.commit()

        # 2. Resolve dispatch order via the shared dependency resolver (§8) instead
        # of a hardcoded single-department check. Pollution depends on Land and
        # Electricity, so it lands in a later wave than both of them.
        execution_plan = resolve_execution_order(PLANT_VERIFICATION_SERVICES)
        first_wave_services = {step.service for step in execution_plan if step.wave == 1}

        # 2a. Dispatch the first wave (Land + Electricity have no prerequisites).
        land_task = self.land_adapter.verify_land(request.land_survey_number, request.organization_pan)
        elec_task = self.elec_adapter.verify_electricity(request.electricity_application_number, request.organization_pan)
        assert {"LAND_SERVICE", "ELECTRICITY_SERVICE"} <= first_wave_services

        land_res, elec_res = await asyncio.gather(land_task, elec_task, return_exceptions=False)

        # 3. Process Land Result
        land_canon = None
        land_pan_match = False
        land_summary = "Land check pending"
        if land_res["success"] and land_res["data"]:
            raw = land_res["data"]
            land_canon = RuleBasedMapper.transform_land(raw, request.organization_pan, db=db)
            normalized_request_pan = request.organization_pan.strip().upper()
            land_pan_match = (
                land_canon.organization_pan.strip().upper() == normalized_request_pan
            ) if land_canon and land_canon.organization_pan else False
            land_summary = f"Survey {request.land_survey_number}: Mutation {land_canon.land_details.mutation_status if land_canon.land_details else 'UNKNOWN'}"
        else:
            land_summary = f"Land call failed: {land_res.get('error')}"

        db.add(DepartmentStepExecution(
            transaction_id=txn_id,
            department_code="LAND",
            status="SUCCESS" if land_res["success"] else "FAILED",
            http_status_code=land_res.get("status_code"),
            response_time_ms=land_res.get("latency_ms", 0.0),
            raw_response=json.dumps(land_res.get("data")),
            canonical_fragment=json.dumps(land_canon.model_dump() if land_canon else None),
            error_message=land_res.get("error")
        ))

        # 4. Process Electricity Result
        elec_canon = None
        elec_pan_match = False
        elec_summary = "Electricity check pending"
        if elec_res["success"] and elec_res["data"]:
            raw = elec_res["data"]
            elec_canon = RuleBasedMapper.transform_electricity(raw, request.organization_pan, db=db)
            elec_pan_match = raw.get("pan_match", True)
            elec_summary = f"App {request.electricity_application_number}: Status {elec_canon.electricity_details.application_status if elec_canon.electricity_details else 'UNKNOWN'}, Dues: {elec_canon.electricity_details.outstanding_dues if elec_canon.electricity_details else 'UNKNOWN'}"
        else:
            elec_summary = f"Electricity call failed: {elec_res.get('error')}"

        db.add(DepartmentStepExecution(
            transaction_id=txn_id,
            department_code="ELECTRICITY",
            status="SUCCESS" if elec_res["success"] else "FAILED",
            http_status_code=elec_res.get("status_code"),
            response_time_ms=elec_res.get("latency_ms", 0.0),
            raw_response=json.dumps(elec_res.get("data")),
            canonical_fragment=json.dumps(elec_canon.model_dump() if elec_canon else None),
            error_message=elec_res.get("error")
        ))

        # 4a. Gate the second wave: Pollution only dispatches once ALL of its
        # prerequisite departments are fully approved (MPCB's Consent to
        # Establish requires a VERIFIED Land Ownership Certificate, not merely
        # a submitted land record), not just Land.
        dependency_satisfied = {
            "LAND": PolicyEngine.is_land_approved(land_canon),
            "ELECTRICITY": PolicyEngine.is_electricity_approved(elec_canon),
        }
        unmet_dependencies = [dep for dep in POLLUTION_DEPENDENCIES if not dependency_satisfied.get(dep, False)]
        pollution_dispatched = not unmet_dependencies

        if pollution_dispatched:
            poll_res = await self.poll_adapter.verify_pollution(
                request.pollution_application_number, request.organization_pan, request.industry_type
            )
        else:
            poll_res = {
                "success": False,
                "data": None,
                "status_code": None,
                "latency_ms": 0.0,
                "error": f"Pollution verification blocked: unmet prerequisite department(s): {', '.join(unmet_dependencies)}",
            }

        # 5. Process Pollution Result
        poll_canon = None
        poll_pan_match = False
        poll_summary = "Pollution check pending"
        if poll_res["success"] and poll_res["data"]:
            raw = poll_res["data"]
            poll_canon = RuleBasedMapper.transform_pollution(raw, request.organization_pan, db=db)
            checks = raw.get("checks", {})
            poll_pan_match = checks.get("pan_match", True) if isinstance(checks, dict) else True
            poll_summary = f"Consent {request.pollution_application_number}: {poll_canon.pollution_details.consent_status if poll_canon.pollution_details else 'UNKNOWN'}, Compliance: {poll_canon.pollution_details.compliance_status if poll_canon.pollution_details else 'UNKNOWN'}"
        else:
            poll_summary = f"Pollution call failed: {poll_res.get('error')}"

        db.add(DepartmentStepExecution(
            transaction_id=txn_id,
            department_code="POLLUTION",
            status="SUCCESS" if poll_res["success"] else "FAILED",
            http_status_code=poll_res.get("status_code"),
            response_time_ms=poll_res.get("latency_ms", 0.0),
            raw_response=json.dumps(poll_res.get("data")),
            canonical_fragment=json.dumps(poll_canon.model_dump() if poll_canon else None),
            error_message=poll_res.get("error")
        ))

        # 6. Merge into Unified Canonical Model
        unified_canonical = RuleBasedMapper.merge_to_unified_project(
            project_name=request.project_name,
            land_canon=land_canon,
            elec_canon=elec_canon,
            poll_canon=poll_canon,
        )

        # 7. Evaluate Policy Engine
        pan_verified, _ = PolicyEngine.verify_pan_identity(
            project_pan=request.organization_pan,
            land_pan=land_canon.organization_pan if land_canon else None,
            elec_pan=elec_canon.organization_pan if elec_canon else None,
            poll_pan=poll_canon.organization_pan if poll_canon else None,
        )

        # Pollution hasn't been contacted when it's blocked on unmet prerequisites,
        # so its pan_match (which defaults to False) must not count against
        # identity verification here -- only departments actually queried do.
        identity_pan_match = land_pan_match and elec_pan_match and (poll_pan_match if pollution_dispatched else True)

        overall_status, next_action, _ = PolicyEngine.evaluate_overall_clearance(
            canonical=unified_canonical,
            pan_verified=pan_verified and identity_pan_match,
        )

        unified_canonical.status = overall_status

        # 8. Update Persistent Transaction Record
        txn_record.overall_status = overall_status
        txn_record.canonical_payload = json.dumps(unified_canonical.model_dump())
        txn_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()

        # 9. Audit Logging
        elapsed_total_ms = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000
        db.add(PlatformAuditLog(
            transaction_id=txn_id,
            actor_email=user.email or user.organization_pan,
            masked_pan=mask_pan(request.organization_pan),
            endpoint="/api/projects/verify-plant",
            action="VERIFY_PLANT_CLEARANCE",
            outcome=overall_status,
            response_code=200,
            response_time_ms=elapsed_total_ms,
        ))
        db.commit()

        # 10. Build Department Checks List
        checks_list = [
            DepartmentCheckResult(
                department="LAND",
                status="SUCCESS" if land_res["success"] else "UNAVAILABLE",
                http_code=land_res.get("status_code"),
                response_time_ms=land_res.get("latency_ms", 0.0),
                pan_match=land_pan_match,
                summary=land_summary,
                raw_facts=land_res.get("data"),
                error=land_res.get("error")
            ),
            DepartmentCheckResult(
                department="ELECTRICITY",
                status="SUCCESS" if elec_res["success"] else "UNAVAILABLE",
                http_code=elec_res.get("status_code"),
                response_time_ms=elec_res.get("latency_ms", 0.0),
                pan_match=elec_pan_match,
                summary=elec_summary,
                raw_facts=elec_res.get("data"),
                error=elec_res.get("error")
            ),
            DepartmentCheckResult(
                department="POLLUTION",
                status="SUCCESS" if poll_res["success"] else "UNAVAILABLE",
                http_code=poll_res.get("status_code"),
                response_time_ms=poll_res.get("latency_ms", 0.0),
                pan_match=poll_pan_match,
                summary=poll_summary,
                raw_facts=poll_res.get("data"),
                error=poll_res.get("error")
            ),
        ]

        return ProjectVerificationResponse(
            transaction_id=txn_id,
            project_name=request.project_name,
            organization_pan=request.organization_pan,
            organization_name=user.organization_name,
            overall_clearance_status=overall_status,
            pan_identity_verified=pan_verified and identity_pan_match,
            department_checks=checks_list,
            canonical_project_state=unified_canonical,
            recommended_next_action=next_action,
        )
