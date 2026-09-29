import json
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.electricity import (
    ElectricityApplication,
    ElectricityConnection,
    ApiConsumer,
)
from app.schemas.requests import AdminStateTransitionRequest


VALID_APPLICATION_STATUSES = {
    "SUBMITTED",
    "UNDER_SCRUTINY",
    "PENDING",
    "APPROVED",
    "REJECTED",
    "UNDER_INSPECTION",
}

VALID_INSPECTION_STATUSES = {
    "NOT_REQUIRED",
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
}

VALID_METER_STATUSES = {
    "NOT_INSTALLED",
    "INSTALLATION_SCHEDULED",
    "INSTALLED",
}

VALID_CONNECTION_STATUSES = {
    "NOT_CONNECTED",
    "READY_FOR_ENERGIZATION",
    "ENERGIZED",
    "DISCONNECTED",
}

VALID_SECURITY_DEPOSIT_STATUSES = {
    "PENDING",
    "PAID",
    "WAIVED",
    "NOT_REQUIRED",
}


class ElectricityService:

    @staticmethod
    def seed_initial_data(db: Session) -> None:
        """Seed API consumers, applications, and connections if database is newly initialized."""
        # 1. Seed API Consumers
        if db.query(ApiConsumer).count() == 0:
            consumers = [
                ApiConsumer(
                    consumer_id="INTEROP-PLATFORM",
                    api_key="elec_live_interop_key_991",
                    is_active=True,
                    allowed_scopes=json.dumps(["/api/electricity/*", "/api/audit"])
                ),
                ApiConsumer(
                    consumer_id="INDUSTRIAL-CLEARANCE",
                    api_key="elec_live_clearance_key_552",
                    is_active=True,
                    allowed_scopes=json.dumps(["/api/electricity/*"])
                ),
                ApiConsumer(
                    consumer_id="DEMO-FRONTEND",
                    api_key="elec_demo_key_101",
                    is_active=True,
                    allowed_scopes=json.dumps(["/api/electricity/*", "/api/admin/*", "/api/audit"])
                ),
                ApiConsumer(
                    consumer_id="ADMIN-CLIENT",
                    api_key="elec_admin_secret_key_888",
                    is_active=True,
                    allowed_scopes=json.dumps(["*"])
                ),
            ]
            db.add_all(consumers)
            db.commit()

        # 2. Seed Applications
        if db.query(ElectricityApplication).count() == 0:
            apps = [
                # App 1001: Success Demo
                ElectricityApplication(
                    application_number="ELEC-2026-00101",
                    consumer_number="CONS-778899",
                    applicant_name="ABC Industries Pvt Ltd",
                    applicant_pan="ABCDE1234F",
                    premises_address="Plot 42, MIDC Industrial Area Phase II, Chakan",
                    district="Pune",
                    taluka="Khed",
                    village="Chakan",
                    supply_category="HT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="500",
                    requested_load_unit="KW",
                    sanctioned_load="500",
                    sanctioned_load_unit="KW",
                    application_status="APPROVED",
                    inspection_status="COMPLETED",
                    meter_status="INSTALLED",
                    connection_status="ENERGIZED",
                    outstanding_dues=False,
                    security_deposit_status="PAID",
                    application_date=datetime.datetime(2026, 7, 10, 9, 30),
                    last_updated=datetime.datetime(2026, 8, 20, 14, 30),
                    inspection_reference="INSP-PN-2026-0811"
                ),
                # App 1002: Main Asynchronous Workflow Demo (Starts PENDING)
                ElectricityApplication(
                    application_number="ELEC-2026-00102",
                    consumer_number=None,
                    applicant_name="XYZ Manufacturing Pvt Ltd",
                    applicant_pan="FGHIJ5678K",
                    premises_address="Survey No 108/2, Talegaon Industrial Zone",
                    district="Pune",
                    taluka="Maval",
                    village="Talegaon Dabhade",
                    supply_category="HT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="750",
                    requested_load_unit="KW",
                    sanctioned_load="750",
                    sanctioned_load_unit="KW",
                    application_status="PENDING",
                    inspection_status="PENDING",
                    meter_status="NOT_INSTALLED",
                    connection_status="NOT_CONNECTED",
                    outstanding_dues=False,
                    security_deposit_status="PENDING",
                    application_date=datetime.datetime(2026, 8, 15, 10, 0),
                    last_updated=datetime.datetime(2026, 8, 15, 10, 0),
                ),
                # App 1003: Approved but Outstanding Dues & Not Connected
                ElectricityApplication(
                    application_number="ELEC-2026-00103",
                    consumer_number=None,
                    applicant_name="DEF Industries Pvt Ltd",
                    applicant_pan="LMNOP9012Q",
                    premises_address="Sector 19, Waluj Industrial Area",
                    district="Chhatrapati Sambhajinagar",
                    taluka="Gangapur",
                    village="Waluj",
                    supply_category="HT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="1000",
                    requested_load_unit="KW",
                    sanctioned_load="800",
                    sanctioned_load_unit="KW",
                    application_status="APPROVED",
                    inspection_status="COMPLETED",
                    meter_status="INSTALLED",
                    connection_status="NOT_CONNECTED",
                    outstanding_dues=True,
                    security_deposit_status="PAID",
                    application_date=datetime.datetime(2026, 7, 22, 11, 15),
                    last_updated=datetime.datetime(2026, 8, 25, 16, 45),
                    inspection_reference="INSP-CSN-2026-0399"
                ),
                # App 1004: Rejected / Inspection Failed
                ElectricityApplication(
                    application_number="ELEC-2026-00104",
                    consumer_number=None,
                    applicant_name="RST Industries Pvt Ltd",
                    applicant_pan="RSTUV3456W",
                    premises_address="Gat No 310, Kurkumbh Chemical Zone",
                    district="Pune",
                    taluka="Daund",
                    village="Kurkumbh",
                    supply_category="LT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="300",
                    requested_load_unit="KW",
                    sanctioned_load="300",
                    sanctioned_load_unit="KW",
                    application_status="REJECTED",
                    inspection_status="FAILED",
                    meter_status="NOT_INSTALLED",
                    connection_status="NOT_CONNECTED",
                    outstanding_dues=False,
                    security_deposit_status="NOT_REQUIRED",
                    rejection_reason="Electrical infrastructure inspection failed",
                    application_date=datetime.datetime(2026, 8, 1, 14, 0),
                    last_updated=datetime.datetime(2026, 8, 18, 17, 30),
                    inspection_reference="INSP-PN-2026-0922"
                ),
                # App 1005: Same Company (ABC Industries) but with Dues
                ElectricityApplication(
                    application_number="ELEC-2026-00105",
                    consumer_number="CONS-552211",
                    applicant_name="ABC Industries Pvt Ltd",
                    applicant_pan="ABCDE1234F",
                    premises_address="Gat 88, Ranjangaon Mega Industrial Park",
                    district="Pune",
                    taluka="Shirur",
                    village="Ranjangaon",
                    supply_category="LT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="250",
                    requested_load_unit="KW",
                    sanctioned_load="250",
                    sanctioned_load_unit="KW",
                    application_status="APPROVED",
                    inspection_status="COMPLETED",
                    meter_status="INSTALLED",
                    connection_status="ENERGIZED",
                    outstanding_dues=True,
                    security_deposit_status="PAID",
                    application_date=datetime.datetime(2026, 6, 5, 10, 0),
                    last_updated=datetime.datetime(2026, 7, 12, 12, 0),
                    inspection_reference="INSP-PN-2026-0412"
                ),
                # App 1006: Intermediate State (UNDER_INSPECTION / IN_PROGRESS)
                ElectricityApplication(
                    application_number="ELEC-2026-00106",
                    consumer_number=None,
                    applicant_name="PQR Industries Pvt Ltd",
                    applicant_pan="PQRWX7890Y",
                    premises_address="Plot B-14, Butibori Industrial Estate",
                    district="Nagpur",
                    taluka="Nagpur Rural",
                    village="Butibori",
                    supply_category="HT-IND",
                    connection_type="INDUSTRIAL",
                    requested_load="600",
                    requested_load_unit="KW",
                    sanctioned_load="600",
                    sanctioned_load_unit="KW",
                    application_status="UNDER_INSPECTION",
                    inspection_status="IN_PROGRESS",
                    meter_status="NOT_INSTALLED",
                    connection_status="NOT_CONNECTED",
                    outstanding_dues=False,
                    security_deposit_status="PAID",
                    application_date=datetime.datetime(2026, 8, 20, 11, 0),
                    last_updated=datetime.datetime(2026, 9, 1, 15, 0),
                    inspection_reference="INSP-NG-2026-0104"
                ),
            ]
            db.add_all(apps)
            db.commit()

        # 3. Seed Existing Connections
        if db.query(ElectricityConnection).count() == 0:
            connections = [
                ElectricityConnection(
                    consumer_number="CONS-778899",
                    application_number="ELEC-2026-00101",
                    applicant_name="ABC Industries Pvt Ltd",
                    applicant_pan="ABCDE1234F",
                    premises_address="Plot 42, MIDC Industrial Area Phase II, Chakan",
                    supply_category="HT-IND",
                    connection_type="INDUSTRIAL",
                    sanctioned_load="500",
                    sanctioned_load_unit="KW",
                    meter_number="MTR-881290",
                    meter_status="INSTALLED",
                    connection_status="ENERGIZED",
                    outstanding_dues=False,
                    energization_date=datetime.datetime(2026, 8, 20, 14, 30),
                    last_updated=datetime.datetime(2026, 8, 20, 14, 30),
                ),
                ElectricityConnection(
                    consumer_number="CONS-552211",
                    application_number="ELEC-2026-00105",
                    applicant_name="ABC Industries Pvt Ltd",
                    applicant_pan="ABCDE1234F",
                    premises_address="Gat 88, Ranjangaon Mega Industrial Park",
                    supply_category="LT-IND",
                    connection_type="INDUSTRIAL",
                    sanctioned_load="250",
                    sanctioned_load_unit="KW",
                    meter_number="MTR-339912",
                    meter_status="INSTALLED",
                    connection_status="ENERGIZED",
                    outstanding_dues=True,
                    energization_date=datetime.datetime(2026, 7, 12, 12, 0),
                    last_updated=datetime.datetime(2026, 7, 12, 12, 0),
                ),
            ]
            db.add_all(connections)
            db.commit()

    @staticmethod
    def get_application_by_number(
        db: Session,
        application_number: str
    ) -> Optional[ElectricityApplication]:
        """Fetch application by application_number."""
        return db.query(ElectricityApplication).filter(
            ElectricityApplication.application_number == application_number
        ).first()

    @staticmethod
    def get_connection_by_consumer_number(
        db: Session,
        consumer_number: str
    ) -> Optional[ElectricityConnection]:
        """Fetch connection by consumer_number."""
        return db.query(ElectricityConnection).filter(
            ElectricityConnection.consumer_number == consumer_number
        ).first()

    @staticmethod
    def to_legacy_application_dict(app: ElectricityApplication) -> Dict[str, Any]:
        """Serialize internal application model to the department-native legacy schema."""
        return {
            "appl_no": app.application_number,
            "cons_no": app.consumer_number,
            "cust_name": app.applicant_name,
            "cust_pan": app.applicant_pan,
            "load_req": app.requested_load,
            "load_unit": app.requested_load_unit,
            "load_sanc": app.sanctioned_load,
            "load_sanc_unit": app.sanctioned_load_unit,
            "cat_code": app.supply_category,
            "conn_type": app.connection_type,
            "appl_stat": app.application_status,
            "insp_stat": app.inspection_status,
            "meter_stat": app.meter_status,
            "conn_stat": app.connection_status,
            "dues_flag": app.outstanding_dues,
            "sec_dep": app.security_deposit_status,
            "appl_dt": app.application_date.isoformat() if app.application_date else None,
            "last_upd": app.last_updated.isoformat() if app.last_updated else None,
            "rej_reason": app.rejection_reason,
        }

    @staticmethod
    def to_legacy_connection_dict(conn: ElectricityConnection) -> Dict[str, Any]:
        """Serialize internal connection model to the department-native legacy schema."""
        return {
            "cons_no": conn.consumer_number,
            "appl_no": conn.application_number,
            "cust_name": conn.applicant_name,
            "cust_pan": conn.applicant_pan,
            "cat_code": conn.supply_category,
            "conn_type": conn.connection_type,
            "load_sanc": conn.sanctioned_load,
            "load_sanc_unit": conn.sanctioned_load_unit,
            "meter_no": conn.meter_number,
            "meter_stat": conn.meter_status,
            "conn_stat": conn.connection_status,
            "dues_flag": conn.outstanding_dues,
            "energized_dt": conn.energization_date.isoformat() if conn.energization_date else None,
        }

    @staticmethod
    def update_application_state(
        db: Session,
        req: AdminStateTransitionRequest
    ) -> ElectricityApplication:
        """Validate and mutate electricity application state for demo/admin orchestration."""
        app = ElectricityService.get_application_by_number(db, req.application_number)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "NOT_FOUND",
                    "department": "ELECTRICITY_DISTRIBUTION",
                    "message": "Electricity application not found for state transition",
                    "application_number": req.application_number
                }
            )

        # Validate status enums if passed
        if req.application_status:
            stat_upper = req.application_status.strip().upper()
            if stat_upper not in VALID_APPLICATION_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_STATE_TRANSITION",
                        "message": f"Invalid application_status '{req.application_status}'. Allowed: {sorted(VALID_APPLICATION_STATUSES)}"
                    }
                )
            app.application_status = stat_upper

        if req.inspection_status:
            insp_upper = req.inspection_status.strip().upper()
            if insp_upper not in VALID_INSPECTION_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_STATE_TRANSITION",
                        "message": f"Invalid inspection_status '{req.inspection_status}'. Allowed: {sorted(VALID_INSPECTION_STATUSES)}"
                    }
                )
            app.inspection_status = insp_upper

        if req.meter_status:
            meter_upper = req.meter_status.strip().upper()
            if meter_upper not in VALID_METER_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_STATE_TRANSITION",
                        "message": f"Invalid meter_status '{req.meter_status}'. Allowed: {sorted(VALID_METER_STATUSES)}"
                    }
                )
            app.meter_status = meter_upper

        if req.connection_status:
            conn_upper = req.connection_status.strip().upper()
            if conn_upper not in VALID_CONNECTION_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_STATE_TRANSITION",
                        "message": f"Invalid connection_status '{req.connection_status}'. Allowed: {sorted(VALID_CONNECTION_STATUSES)}"
                    }
                )
            app.connection_status = conn_upper

        if req.security_deposit_status:
            sec_upper = req.security_deposit_status.strip().upper()
            if sec_upper not in VALID_SECURITY_DEPOSIT_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "status": "INVALID_STATE_TRANSITION",
                        "message": f"Invalid security_deposit_status '{req.security_deposit_status}'. Allowed: {sorted(VALID_SECURITY_DEPOSIT_STATUSES)}"
                    }
                )
            app.security_deposit_status = sec_upper

        if req.rejection_reason is not None:
            app.rejection_reason = req.rejection_reason

        if req.outstanding_dues is not None:
            app.outstanding_dues = req.outstanding_dues

        app.last_updated = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(app)
        return app
