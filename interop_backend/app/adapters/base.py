import time
import asyncio
import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.engine.circuit_breaker import get_circuit_breaker, CircuitOpenException


class BaseDepartmentAdapter:
    def __init__(self, service_name: str, base_url: str, default_api_key: str):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.default_api_key = default_api_key
        self.circuit_breaker = get_circuit_breaker(service_name)

    async def execute_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute an asynchronous HTTP request with Circuit Breaker and Retry."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = {"X-API-Key": self.default_api_key, "Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        start_time = time.time()

        # 1. Circuit Breaker check
        try:
            self.circuit_breaker.before_call(self.service_name)
        except CircuitOpenException as coe:
            elapsed_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": 503,
                "data": None,
                "error": str(coe),
                "circuit_open": True,
                "latency_ms": elapsed_ms,
            }

        # 2. Retry loop with exponential backoff
        attempts = 0
        last_error = None
        last_status = None

        while attempts <= settings.HTTP_MAX_RETRIES:
            attempts += 1
            try:
                async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_body,
                        headers=req_headers
                    )
                    elapsed_ms = (time.time() - start_time) * 1000
                    last_status = response.status_code

                    # If department returned 503 (simulated failure), treat as candidate for retry
                    if response.status_code == 503 and attempts <= settings.HTTP_MAX_RETRIES:
                        await asyncio.sleep(0.5 * attempts)
                        continue

                    # Success or expected business response (200, 400, 404, etc.)
                    if response.is_success or response.status_code in [200, 400, 404, 422]:
                        self.circuit_breaker.record_success()
                        try:
                            data = response.json()
                        except Exception:
                            data = {"raw": response.text}
                        return {
                            "success": response.is_success,
                            "status_code": response.status_code,
                            "data": data,
                            "error": None if response.is_success else data.get("message", "Department returned error"),
                            "latency_ms": elapsed_ms,
                        }
                    else:
                        self.circuit_breaker.record_failure()
                        return {
                            "success": False,
                            "status_code": response.status_code,
                            "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                            "error": f"HTTP {response.status_code}: {response.text}",
                            "latency_ms": elapsed_ms,
                        }

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = str(exc)
                if attempts <= settings.HTTP_MAX_RETRIES:
                    await asyncio.sleep(0.5 * attempts)
                    continue

        # All retries exhausted
        self.circuit_breaker.record_failure()
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "status_code": last_status or 503,
            "data": None,
            "error": f"Department service unavailable after {attempts} attempts: {last_error}",
            "latency_ms": elapsed_ms,
        }
