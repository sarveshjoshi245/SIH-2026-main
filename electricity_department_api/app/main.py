import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # pyrefly: ignore[missing-import]
from pathlib import Path

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.electricity_service import ElectricityService
from app.utils.transaction import generate_transaction_id
from app.routers import (
    health_router,
    applications_router,
    connections_router,
    verification_router,
    status_router,
    admin_router,
    audit_router,
    portal_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed default data
    db = SessionLocal()
    try:
        ElectricityService.seed_initial_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="""
Authoritative backend API for the State Electricity Distribution Department.

### Architectural Role
Provides authoritative departmental facts (application status, sanctioned loads, inspection results, meter state, dues).
This service exposes department-native schemas and operates independently of external interoperability platforms.

**Disclaimer:** All records and credentials in this system are synthetic and intended strictly for testing/demonstration.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Public health and uptime monitoring"},
        {"name": "Electricity Applications", "description": "Raw departmental electricity application queries"},
        {"name": "Electricity Connections", "description": "Existing consumer connection queries"},
        {"name": "Verification", "description": "Departmental identity and prerequisite fact verification"},
        {"name": "Status", "description": "Lightweight status polling for async dependencies"},
        {"name": "Admin Demo", "description": "Demo-only state mutation for hackathon simulations"},
        {"name": "Audit", "description": "Department-side access and trace logs"},
        {"name": "Public Portal (UI)", "description": "Read-only views for the department website"},
    ]
)

# Enable CORS for frontend demo integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_and_header_middleware(request: Request, call_next):
    # Capture or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID")
    request.state.correlation_id = correlation_id

    response = await call_next(request)

    # Attach correlation ID and transaction ID to response headers if present
    if correlation_id:
        response.headers["X-Correlation-ID"] = correlation_id
    if hasattr(request.state, "transaction_id"):
        response.headers["X-Transaction-ID"] = request.state.transaction_id

    return response


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Ensure consistent structured departmental error responses."""
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    tid = getattr(request.state, "transaction_id", generate_transaction_id())
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "ERROR",
            "department": "ELECTRICITY_DISTRIBUTION",
            "message": str(exc.detail),
            "transaction_id": tid
        }
    )


# Include Routers
app.include_router(health_router)
app.include_router(applications_router)
app.include_router(connections_router)
app.include_router(verification_router)
app.include_router(status_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(portal_router)  # public website views (read-only)

# Mount the static public directory for the Electricity UI Demo
_THIS_DIR = Path(__file__).resolve().parent          # …/electricity_department_api/app
_PUBLIC_DIR = _THIS_DIR.parent / "public"            # …/electricity_department_api/public
if _PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_PUBLIC_DIR), html=True), name="public")
