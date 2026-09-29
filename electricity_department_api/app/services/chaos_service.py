import asyncio
import random
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from app.config import settings
from app.utils.transaction import generate_transaction_id


class ChaosService:
    @staticmethod
    async def maybe_simulate_chaos(
        endpoint_type: str,  # "application", "verify", "status"
        transaction_id: Optional[str] = None,
        bypass: bool = False
    ):
        """Optionally trigger 503 unavailability or simulated latency if chaos is enabled."""
        if not settings.CHAOS_ENABLED or bypass:
            return

        tid = transaction_id or generate_transaction_id()

        # Check for simulated latency
        if random.random() < settings.SIMULATED_DELAY_RATE:
            delay_sec = settings.SIMULATED_DELAY_MS / 1000.0
            await asyncio.sleep(delay_sec)

        # Check for failure rates based on endpoint
        failure_rate = 0.0
        if endpoint_type == "application":
            failure_rate = settings.APPLICATION_FAILURE_RATE
        elif endpoint_type == "verify":
            failure_rate = settings.VERIFY_FAILURE_RATE
        elif endpoint_type == "status":
            failure_rate = settings.STATUS_FAILURE_RATE

        if random.random() < failure_rate:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "DEPARTMENT_UNAVAILABLE",
                    "department": "ELECTRICITY_DISTRIBUTION",
                    "message": "Electricity Department systems are temporarily unavailable",
                    "retryable": True,
                    "transaction_id": tid
                }
            )

    @staticmethod
    def apply_schema_drift(data: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """Optionally apply schema drift (15-20% chance or force=True) to departmental field names."""
        should_drift = force or (settings.CHAOS_ENABLED and random.random() < settings.SCHEMA_DRIFT_RATE)
        if not should_drift:
            return data

        # Map legacy keys to drifted keys (values untouched)
        drift_map = {
            "appl_no": "application_no",
            "cust_name": "consumer_name",
            "load_sanc": "sanctioned_load",
            "appl_stat": "application_status",
            "conn_stat": "connection_status",
            "insp_stat": "inspection_status",
            "meter_stat": "meter_status",
            "dues_flag": "outstanding_dues_flag",
            "sec_dep": "security_deposit",
        }

        drifted_data = {}
        for k, v in data.items():
            new_key = drift_map.get(k, k)
            drifted_data[new_key] = v

        return drifted_data
