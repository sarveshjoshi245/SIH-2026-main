from app.routers.auth import router as auth_router
from app.routers.consent import router as consent_router
from app.routers.projects import router as projects_router
from app.routers.canonical import router as canonical_router
from app.routers.schema_drift import router as schema_drift_router
from app.routers.departments import router as departments_router
from app.routers.audit import router as audit_router
from app.routers.interview import router as interview_router

__all__ = [
    "auth_router",
    "consent_router",
    "projects_router",
    "canonical_router",
    "schema_drift_router",
    "departments_router",
    "audit_router",
    "interview_router",
]
