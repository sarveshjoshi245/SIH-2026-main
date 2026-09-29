from fastapi import APIRouter
from app.schemas.responses import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Public endpoint to verify operational status of the Electricity Distribution Department service."
)
def get_health():
    return HealthResponse(
        status="UP",
        service="ELECTRICITY_DISTRIBUTION_DEPARTMENT"
    )
