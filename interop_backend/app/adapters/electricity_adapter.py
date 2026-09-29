from typing import Dict, Any, Optional
from app.config import settings
from app.adapters.base import BaseDepartmentAdapter


class ElectricityAdapter(BaseDepartmentAdapter):
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(
            service_name="ELECTRICITY",
            base_url=base_url or settings.ELECTRICITY_API_URL,
            default_api_key=api_key or settings.ELECTRICITY_API_KEY
        )

    async def get_application(self, application_number: str) -> Dict[str, Any]:
        """Call GET /api/electricity/applications/{application_number}."""
        return await self.execute_request("GET", f"/api/electricity/applications/{application_number}")

    async def verify_electricity(self, application_number: str, pan: str) -> Dict[str, Any]:
        """Call POST /api/electricity/verify."""
        return await self.execute_request(
            "POST",
            "/api/electricity/verify",
            json_body={"application_number": application_number, "pan": pan}
        )

    async def get_status(self, application_number: str) -> Dict[str, Any]:
        """Call GET /api/electricity/status/{application_number}."""
        return await self.execute_request("GET", f"/api/electricity/status/{application_number}")
