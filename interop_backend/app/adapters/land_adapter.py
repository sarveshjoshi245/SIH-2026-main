from typing import Dict, Any, Optional
from app.config import settings
from app.adapters.base import BaseDepartmentAdapter


class LandAdapter(BaseDepartmentAdapter):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(
            service_name="LAND",
            base_url=base_url or settings.LAND_API_URL,
            default_api_key=api_key or settings.LAND_API_KEY
        )

    async def get_record(self, survey_number: str) -> Dict[str, Any]:
        """Call GET /api/land/records/{surveyNumber}."""
        return await self.execute_request("GET", f"/api/land/records/{survey_number}")

    async def verify_land(self, survey_number: str, pan: str) -> Dict[str, Any]:
        """Call POST /api/land/verify."""
        return await self.execute_request(
            "POST",
            "/api/land/verify",
            json_body={"surveyNumber": survey_number, "pan": pan}
        )

    async def get_status(self, survey_number: str) -> Dict[str, Any]:
        """Call GET /api/land/status/{surveyNumber}."""
        return await self.execute_request("GET", f"/api/land/status/{survey_number}")
