import asyncio
from typing import Dict, Any
from fastapi import APIRouter
from app.adapters.land_adapter import LandAdapter
from app.adapters.electricity_adapter import ElectricityAdapter
from app.adapters.pollution_adapter import PollutionAdapter

router = APIRouter(prefix="/api/departments", tags=["Department Health & Connectivity"])


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Check Connectivity to all 3 Department APIs",
    description="Probes the live status and circuit breakers for Land, Electricity, and Pollution departmental systems."
)
async def check_departments_health():
    land_adapter = LandAdapter()
    elec_adapter = ElectricityAdapter()
    poll_adapter = PollutionAdapter()

    # Ping health / status on all 3
    land_task = land_adapter.get_status("101")
    elec_task = elec_adapter.execute_request("GET", "/health")
    poll_task = poll_adapter.get_status("MPCB-8821")

    land_res, elec_res, poll_res = await asyncio.gather(land_task, elec_task, poll_task, return_exceptions=False)

    return {
        "status": "UP" if (land_res["success"] and elec_res["success"] and poll_res["success"]) else "DEGRADED",
        "departments": {
            "LAND": {
                "reachable": land_res["success"],
                "status_code": land_res.get("status_code"),
                "latency_ms": land_res.get("latency_ms"),
                "circuit_state": land_adapter.circuit_breaker.state,
                "error": land_res.get("error")
            },
            "ELECTRICITY": {
                "reachable": elec_res["success"],
                "status_code": elec_res.get("status_code"),
                "latency_ms": elec_res.get("latency_ms"),
                "circuit_state": elec_adapter.circuit_breaker.state,
                "error": elec_res.get("error")
            },
            "POLLUTION": {
                "reachable": poll_res["success"],
                "status_code": poll_res.get("status_code"),
                "latency_ms": poll_res.get("latency_ms"),
                "circuit_state": poll_adapter.circuit_breaker.state,
                "error": poll_res.get("error")
            }
        }
    }
