import os
import sys
from typing import Dict, Any

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app, seed_database_defaults
from app.auth.jwt_handler import create_access_token
from app.adapters.land_adapter import LandAdapter
from app.adapters.electricity_adapter import ElectricityAdapter
from app.adapters.pollution_adapter import PollutionAdapter
from app.routers.projects import workflow_engine

TEST_DB_URL = "sqlite:///./test_interop_platform.db"

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Mock Adapters for Deterministic Testing
class MockLandAdapter(LandAdapter):
    async def verify_land(self, survey_number: str, pan: str) -> Dict[str, Any]:
        if survey_number == "999":  # Simulated Outage
            return {"success": False, "status_code": 503, "data": None, "error": "Simulated Land Outage", "latency_ms": 15.0}
        if survey_number == "101":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "survey_number": "101",
                    "canonical": {
                        "survey_number": "101",
                        "owner_name": "ABC Industries Pvt Ltd",
                        "owner_pan": "ABCDE1234F",
                        "area_hectares": 4.5,
                        "area_unit": "HECTARES",
                        "mutation_status": "APPROVED",
                        "land_type": "INDUSTRIAL",
                        "encumbrance": False,
                        "court_case": False,
                        "district": "Pune",
                        "location": "Khed, Chakan"
                    },
                    "dependency_status": "RESOLVED"
                },
                "latency_ms": 12.0
            }
        elif survey_number == "103":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "survey_number": "103",
                    "canonical": {
                        "survey_number": "103",
                        "owner_name": "XYZ Manufacturing Pvt Ltd",
                        "owner_pan": "FGHIJ5678K",
                        "mutation_status": "PENDING",
                        "land_type": "INDUSTRIAL",
                        "encumbrance": False,
                        "court_case": False,
                        "district": "Pune"
                    },
                    "dependency_status": "WAITING"
                },
                "latency_ms": 10.0
            }
        return {"success": False, "status_code": 404, "data": None, "error": "Not Found", "latency_ms": 5.0}


class MockElectricityAdapter(ElectricityAdapter):
    async def verify_electricity(self, application_number: str, pan: str) -> Dict[str, Any]:
        if application_number == "ELEC-OUTAGE":
            return {"success": False, "status_code": 503, "data": None, "error": "Simulated Electricity Outage", "latency_ms": 20.0}
        if application_number == "ELEC-2026-00101":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "transaction_id": "ELEC-VERIFY-101",
                    "status": "SUCCESS",
                    "pan_match": (pan == "ABCDE1234F"),
                    "application": {
                        "appl_no": "ELEC-2026-00101",
                        "cust_name": "ABC Industries Pvt Ltd",
                        "cust_pan": "ABCDE1234F",
                        "load_req": "500",
                        "load_sanc": "500",
                        "cat_code": "HT-IND",
                        "appl_stat": "APPROVED",
                        "insp_stat": "COMPLETED",
                        "meter_stat": "INSTALLED",
                        "conn_stat": "ENERGIZED",
                        "dues_flag": False
                    }
                },
                "latency_ms": 15.0
            }
        elif application_number == "ELEC-2026-00102":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "transaction_id": "ELEC-VERIFY-102",
                    "status": "SUCCESS",
                    "pan_match": (pan == "FGHIJ5678K"),
                    "application": {
                        "appl_no": "ELEC-2026-00102",
                        "cust_name": "XYZ Manufacturing Pvt Ltd",
                        "cust_pan": "FGHIJ5678K",
                        "load_req": "750",
                        "load_sanc": "750",
                        "cat_code": "HT-IND",
                        "appl_stat": "PENDING",
                        "insp_stat": "PENDING",
                        "meter_stat": "NOT_INSTALLED",
                        "conn_stat": "NOT_CONNECTED",
                        "dues_flag": False
                    }
                },
                "latency_ms": 14.0
            }
        return {"success": False, "status_code": 404, "data": None, "error": "Not Found", "latency_ms": 8.0}


class MockPollutionAdapter(PollutionAdapter):
    async def verify_pollution(self, application_no: str, pan: str, industry_type: str = "Chemical") -> Dict[str, Any]:
        if application_no == "MPCB-OUTAGE":
            return {"success": False, "status_code": 503, "data": None, "error": "Simulated Pollution Outage", "latency_ms": 25.0}
        if application_no == "MPCB-8821":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "application_no": "MPCB-8821",
                    "project_id": "PROJ-101",
                    "canonical": {
                        "environment_application_number": "MPCB-8821",
                        "project_id": "PROJ-101",
                        "organization_name": "ABC Industries Pvt Ltd",
                        "organization_pan": "ABCDE1234F",
                        "consent_type": "CTE",
                        "consent_status": "APPROVED",
                        "compliance_status": "COMPLIANT",
                        "location": "MIDC Pune",
                        "district": "Pune",
                        "industry_type": "Chemical"
                    },
                    "checks": {"pan_match": (pan == "ABCDE1234F")},
                    "dependency_status": "RESOLVED"
                },
                "latency_ms": 18.0
            }
        elif application_no == "MPCB-8822":
            return {
                "success": True,
                "status_code": 200,
                "data": {
                    "application_no": "MPCB-8822",
                    "project_id": "PROJ-102",
                    "canonical": {
                        "environment_application_number": "MPCB-8822",
                        "project_id": "PROJ-102",
                        "organization_name": "XYZ Manufacturing Pvt Ltd",
                        "organization_pan": "FGHIJ5678K",
                        "consent_type": "CTE",
                        "consent_status": "PENDING",
                        "compliance_status": "COMPLIANT",
                        "industry_type": "Chemical"
                    },
                    "checks": {"pan_match": (pan == "FGHIJ5678K")},
                    "dependency_status": "WAITING"
                },
                "latency_ms": 16.0
            }
        return {"success": False, "status_code": 404, "data": None, "error": "Not Found", "latency_ms": 6.0}


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database_defaults(db)
    db.close()

    # Inject Mock Adapters into workflow engine
    workflow_engine.land_adapter = MockLandAdapter()
    workflow_engine.elec_adapter = MockElectricityAdapter()
    workflow_engine.poll_adapter = MockPollutionAdapter()

    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def abc_token():
    return create_access_token({
        "sub": "applicant@abcindustries.com",
        "pan": "ABCDE1234F",
        "org": "ABC Industries Pvt Ltd"
    })


@pytest.fixture
def abc_headers(abc_token):
    return {"Authorization": f"Bearer {abc_token}"}


@pytest.fixture
def admin_token():
    return create_access_token({
        "sub": "admin@interop.gov.in",
        "pan": "ADMIN0000A",
        "org": "Interoperability Platform Administration"
    })


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
