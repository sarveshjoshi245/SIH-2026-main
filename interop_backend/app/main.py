import json
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.consent import UserConsent
from app.models.department import Department
from app.auth.jwt_handler import hash_password
from app.routers import (
    auth_router,
    consent_router,
    projects_router,
    canonical_router,
    schema_drift_router,
    departments_router,
    audit_router,
    interview_router,
)


def seed_database_defaults(db):
    """Seed default users, departments, and sample consents if database is fresh."""
    # 1. Seed Users
    if db.query(User).count() == 0:
        demo_users = [
            User(
                email="applicant@abcindustries.com",
                hashed_password=hash_password("SecretPass123"),
                organization_name="ABC Industries Pvt Ltd",
                organization_pan="ABCDE1234F",
                aadhaar_number="111111111101",
                aadhaar_masked="XXXX-XXXX-1101",
                is_aadhaar_verified=True,
                is_active=True
            ),
            User(
                email="applicant@xyzmfg.com",
                hashed_password=hash_password("SecretPass123"),
                organization_name="XYZ Manufacturing Pvt Ltd",
                organization_pan="FGHIJ5678K",
                aadhaar_number="111111111102",
                aadhaar_masked="XXXX-XXXX-1102",
                is_aadhaar_verified=True,
                is_active=True
            ),
            User(
                email="admin@interop.gov.in",
                hashed_password=hash_password("AdminPass123"),
                organization_name="Interoperability Platform Administration",
                organization_pan="ADMIN0000A",
                aadhaar_number="111111111103",
                aadhaar_masked="XXXX-XXXX-1103",
                is_aadhaar_verified=True,
                is_active=True,
                role=User.ROLE_ADMIN
            ),
        ]
        db.add_all(demo_users)
        db.commit()

        # Seed sample active consent for ABC Industries
        abc_user = db.query(User).filter(User.email == "applicant@abcindustries.com").first()
        if abc_user:
            consent = UserConsent(
                user_id=abc_user.id,
                organization_pan="ABCDE1234F",
                purpose="Industrial Manufacturing Plant Establishment Clearance",
                allowed_departments=json.dumps(["LAND", "ELECTRICITY", "POLLUTION"]),
                is_active=True,
                granted_at=datetime.datetime.now(datetime.timezone.utc),
                expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            )
            db.add(consent)

        # Seed sample active consent for XYZ Manufacturing
        xyz_user = db.query(User).filter(User.email == "applicant@xyzmfg.com").first()
        if xyz_user:
            consent = UserConsent(
                user_id=xyz_user.id,
                organization_pan="FGHIJ5678K",
                purpose="Industrial Manufacturing Plant Establishment Clearance",
                allowed_departments=json.dumps(["LAND", "ELECTRICITY", "POLLUTION"]),
                is_active=True,
                granted_at=datetime.datetime.now(datetime.timezone.utc),
                expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
            )
            db.add(consent)

        db.commit()

    # 2. Seed Departments
    if db.query(Department).count() == 0:
        depts = [
            Department(
                code="LAND",
                name="Land Records & Revenue Department",
                base_url=settings.LAND_API_URL,
                auth_header_name="X-API-Key",
                auth_token=settings.LAND_API_KEY,
                is_active=True
            ),
            Department(
                code="ELECTRICITY",
                name="Electricity Distribution Department",
                base_url=settings.ELECTRICITY_API_URL,
                auth_header_name="X-API-Key",
                auth_token=settings.ELECTRICITY_API_KEY,
                is_active=True
            ),
            Department(
                code="POLLUTION",
                name="State Pollution Control Board",
                base_url=settings.POLLUTION_API_URL,
                auth_header_name="X-API-Key",
                auth_token=settings.POLLUTION_API_KEY,
                is_active=True
            ),
        ]
        db.add_all(depts)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_defaults(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="""
# Government Interoperability Layer Platform Backend (PS: SIH26129)

Central interoperability engine connecting heterogeneous departmental systems:
- **Land Records & Revenue** (`http://localhost:4000`)
- **Electricity Distribution Department** (`http://localhost:8000`)
- **Pollution Control Board** (`http://localhost:4002`)

### Core Architectural Features:
1. **Consent Governance:** Strict user consent verification before accessing department facts.
2. **Deterministic Rule-Based Mapper:** Converts native legacy schemas into unified Canonical Models.
3. **Identity Resolution:** Authoritative PAN-based cross-department joining.
4. **Resilience & Circuit Breakers:** Fault tolerance on simulated outages (503s) and graceful partial degradation.
5. **AI-Assisted Schema Drift:** Detects unmapped mutated keys and generates confidence-scored suggestions.
6. **Masked Audit Trail:** Privacy-compliant audit logging with masked PANs (`AB****34F`).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication & Identity", "description": "Enterprise user registration, JWT login, and profile"},
        {"name": "Consent Management", "description": "Citizen and enterprise data access consent governance"},
        {"name": "Plant Clearance Workflow", "description": "Multi-department plant clearance orchestration"},
        {"name": "Canonical Data Transformation", "description": "Deterministic rule-based schema mapping engine"},
        {"name": "AI-Assisted Schema Drift", "description": "Automated schema change detection & suggestion"},
        {"name": "RAG Intake & Conversational Interview", "description": "Conversational project intake, RAG legal reasoning, and deterministic decision engine"},
        {"name": "Department Health & Connectivity", "description": "Downstream departmental API health & circuit status"},
        {"name": "Platform Audit Logging", "description": "Masked compliance and access audit trails"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "UP",
        "service": "INTEROPERABILITY_PLATFORM_BACKEND",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


# Include Routers
app.include_router(interview_router)
app.include_router(auth_router)
app.include_router(consent_router)
app.include_router(projects_router)
app.include_router(canonical_router)
app.include_router(schema_drift_router)
app.include_router(departments_router)
app.include_router(audit_router)
