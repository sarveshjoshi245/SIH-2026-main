from app.routers.health import router as health_router
from app.routers.applications import router as applications_router
from app.routers.connections import router as connections_router
from app.routers.verification import router as verification_router
from app.routers.status import router as status_router
from app.routers.admin import router as admin_router
from app.routers.audit import router as audit_router
from app.routers.portal import router as portal_router

__all__ = [
    "health_router",
    "applications_router",
    "connections_router",
    "verification_router",
    "status_router",
    "admin_router",
    "audit_router",
    "portal_router",
]
