import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    status: str = Field("UP", json_schema_extra={"example": "UP"})
    service: str = Field("ELECTRICITY_DISTRIBUTION_DEPARTMENT", json_schema_extra={"example": "ELECTRICITY_DISTRIBUTION_DEPARTMENT"})


class LegacyApplicationSchema(BaseModel):
    appl_no: str = Field(..., json_schema_extra={"example": "ELEC-2026-00102"})
    cons_no: Optional[str] = Field(None, json_schema_extra={"example": "CONS-778899"})
    cust_name: str = Field(..., json_schema_extra={"example": "XYZ Manufacturing Pvt Ltd"})
    cust_pan: str = Field(..., json_schema_extra={"example": "FGHIJ5678K"})
    load_req: str = Field(..., json_schema_extra={"example": "750"})
    load_unit: str = Field(..., json_schema_extra={"example": "KW"})
    load_sanc: str = Field(..., json_schema_extra={"example": "750"})
    load_sanc_unit: str = Field(..., json_schema_extra={"example": "KW"})
    cat_code: str = Field(..., json_schema_extra={"example": "HT-IND"})
    conn_type: str = Field(..., json_schema_extra={"example": "INDUSTRIAL"})
    appl_stat: str = Field(..., json_schema_extra={"example": "PENDING"})
    insp_stat: str = Field(..., json_schema_extra={"example": "PENDING"})
    meter_stat: str = Field(..., json_schema_extra={"example": "NOT_INSTALLED"})
    conn_stat: str = Field(..., json_schema_extra={"example": "NOT_CONNECTED"})
    dues_flag: bool = Field(..., json_schema_extra={"example": False})
    sec_dep: str = Field(..., json_schema_extra={"example": "PENDING"})
    appl_dt: Optional[str] = Field(None, json_schema_extra={"example": "2026-08-15T10:00:00"})
    last_upd: Optional[str] = Field(None, json_schema_extra={"example": "2026-09-02T18:00:00"})
    rej_reason: Optional[str] = Field(None, json_schema_extra={"example": "Electrical infrastructure inspection failed"})


class LegacyConnectionSchema(BaseModel):
    cons_no: str = Field(..., json_schema_extra={"example": "CONS-778899"})
    appl_no: Optional[str] = Field(None, json_schema_extra={"example": "ELEC-2026-00101"})
    cust_name: str = Field(..., json_schema_extra={"example": "ABC Industries Pvt Ltd"})
    cust_pan: str = Field(..., json_schema_extra={"example": "ABCDE1234F"})
    cat_code: str = Field(..., json_schema_extra={"example": "HT-IND"})
    conn_type: str = Field(..., json_schema_extra={"example": "INDUSTRIAL"})
    load_sanc: str = Field(..., json_schema_extra={"example": "500"})
    load_sanc_unit: str = Field(..., json_schema_extra={"example": "KW"})
    meter_no: Optional[str] = Field(None, json_schema_extra={"example": "MTR-881290"})
    meter_stat: str = Field(..., json_schema_extra={"example": "INSTALLED"})
    conn_stat: str = Field(..., json_schema_extra={"example": "ENERGIZED"})
    dues_flag: bool = Field(..., json_schema_extra={"example": False})
    energized_dt: Optional[str] = Field(None, json_schema_extra={"example": "2026-08-20T14:30:00"})


class VerifyResponse(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "ELEC-TXN-8F12A"})
    status: str = Field("SUCCESS", json_schema_extra={"example": "SUCCESS"})
    pan_match: bool = Field(..., json_schema_extra={"example": True})
    application: Optional[Dict[str, Any]] = Field(None, description="Department-native application facts")
    message: Optional[str] = Field(None, json_schema_extra={"example": "Application verified successfully"})


class StatusResponse(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "ELEC-STATUS-91BC20"})
    application_number: str = Field(..., json_schema_extra={"example": "ELEC-2026-00102"})
    application_status: str = Field(..., json_schema_extra={"example": "PENDING"})
    inspection_status: str = Field(..., json_schema_extra={"example": "PENDING"})
    meter_status: str = Field(..., json_schema_extra={"example": "NOT_INSTALLED"})
    connection_status: str = Field(..., json_schema_extra={"example": "NOT_CONNECTED"})
    last_updated: str = Field(..., json_schema_extra={"example": "2026-09-02T18:00:00"})
    retryable: bool = Field(..., json_schema_extra={"example": True})


class AdminStateTransitionResponse(BaseModel):
    status: str = Field("SUCCESS", json_schema_extra={"example": "SUCCESS"})
    message: str = Field(..., json_schema_extra={"example": "Application state updated successfully (ADMIN DEMO)"})
    application_number: str = Field(..., json_schema_extra={"example": "ELEC-2026-00102"})
    updated_state: Dict[str, Any]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime.datetime
    transaction_id: str
    consumer_id: Optional[str]
    endpoint: str
    application_number: Optional[str]
    outcome: str
    response_code: int
    response_time_ms: float
    failure_type: Optional[str]


class ErrorResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "NOT_FOUND"})
    department: Optional[str] = Field("ELECTRICITY_DISTRIBUTION", json_schema_extra={"example": "ELECTRICITY_DISTRIBUTION"})
    message: str = Field(..., json_schema_extra={"example": "Electricity application not found"})
    application_number: Optional[str] = Field(None, json_schema_extra={"example": "ELEC-999999"})
    retryable: Optional[bool] = Field(None, json_schema_extra={"example": False})
    transaction_id: Optional[str] = Field(None, json_schema_extra={"example": "ELEC-TXN-123456"})
