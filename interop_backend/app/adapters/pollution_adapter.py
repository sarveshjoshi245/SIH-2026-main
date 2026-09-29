from typing import Dict, Any, Optional
from app.config import settings
from app.adapters.base import BaseDepartmentAdapter


class PollutionAdapter(BaseDepartmentAdapter):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(
            service_name="POLLUTION",
            base_url=base_url or settings.POLLUTION_API_URL,
            default_api_key=api_key or settings.POLLUTION_API_KEY
        )

    async def get_application(self, application_no: str) -> Dict[str, Any]:
        """Call GET /api/pollution/applications/{applicationNo}."""
        return await self.execute_request("GET", f"/api/pollution/applications/{application_no}")

    async def verify_pollution(self, application_no: str, pan: str, industry_type: Optional[str] = "Chemical") -> Dict[str, Any]:
        """Call POST /api/pollution/verify."""
        return await self.execute_request(
            "POST",
            "/api/pollution/verify",
            json_body={"applicationNo": application_no, "pan": pan, "industryType": industry_type}
        )

    async def get_status(self, application_no: str) -> Dict[str, Any]:
        """Call GET /api/pollution/status/{applicationNo}."""
        return await self.execute_request("GET", f"/api/pollution/status/{application_no}")
