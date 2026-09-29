"""
Pydantic models for the RAG Intake & Decision Engine module.

Defines the Project Profile schema (§5), decision/execution output schemas (§8.3),
and interview request/response models (§10).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ── Enums ────────────────────────────────────────────────────────────────────

class ProjectType(str, Enum):
    MANUFACTURING = "MANUFACTURING"
    WAREHOUSE = "WAREHOUSE"
    IT_OFFICE = "IT_OFFICE"
    OTHER = "OTHER"


class IndustryType(str, Enum):
    CHEMICAL = "CHEMICAL"
    PHARMACEUTICAL = "PHARMACEUTICAL"
    FOOD_PROCESSING = "FOOD_PROCESSING"
    TEXTILE = "TEXTILE"
    ELECTRONICS = "ELECTRONICS"
    GENERAL = "GENERAL"
    OTHER = "OTHER"


class ServiceName(str, Enum):
    LAND_SERVICE = "LAND_SERVICE"
    ELECTRICITY_SERVICE = "ELECTRICITY_SERVICE"
    POLLUTION_SERVICE = "POLLUTION_SERVICE"


class InterviewState(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class LandOwnership(str, Enum):
    YES = "Yes"
    NO = "No"
    UNDER_ACQUISITION = "Under acquisition"


# ── Project Profile sub-models ───────────────────────────────────────────────

class LocationInfo(BaseModel):
    district: Optional[str] = None
    state: Optional[str] = Field(default="Maharashtra")


class LandInfo(BaseModel):
    required: Optional[bool] = None
    owned: Optional[bool] = None
    ownership_status: Optional[LandOwnership] = None
    area_hectare: Optional[float] = Field(default=None, ge=0)


class ElectricityInfo(BaseModel):
    required: Optional[bool] = None
    required_load_kw: Optional[float] = Field(default=None, ge=0)


class EnvironmentInfo(BaseModel):
    industrial_emissions: Optional[bool] = None
    hazardous_waste: Optional[bool] = None


# ── Project Profile (§5) ────────────────────────────────────────────────────

class ProjectProfile(BaseModel):
    """
    The structured project profile produced by the interview.
    Validated before passing to the decision engine.
    """
    project_type: Optional[ProjectType] = None
    industry_type: Optional[IndustryType] = None
    location: LocationInfo = Field(default_factory=LocationInfo)
    land: LandInfo = Field(default_factory=LandInfo)
    electricity: ElectricityInfo = Field(default_factory=ElectricityInfo)
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo)

    def is_complete(self) -> bool:
        """Check whether all required fields are populated for decision engine input."""
        return all([
            self.project_type is not None,
            self.location.district is not None,
            self.land.required is not None,
            self.electricity.required is not None,
            self.environment.industrial_emissions is not None,
            self.environment.hazardous_waste is not None,
        ])

    def get_missing_fields(self) -> list[str]:
        """Return list of field names still needed."""
        missing = []
        if self.project_type is None:
            missing.append("project_type")
        if self.location.district is None:
            missing.append("location.district")
        if self.land.required is None:
            missing.append("land.required")
        if self.electricity.required is None:
            missing.append("electricity.required")
        if self.environment.industrial_emissions is None:
            missing.append("environment.industrial_emissions")
        if self.environment.hazardous_waste is None:
            missing.append("environment.hazardous_waste")
        return missing


# ── Decision & Execution Plan output (§8.3) ──────────────────────────────────

class ExecutionStep(BaseModel):
    """A single step in the execution plan — one service in one wave."""
    wave: int = Field(ge=1)
    service: str
    depends_on: list[str] = Field(default_factory=list)
    reason: str


class DecisionResult(BaseModel):
    """
    Combined output of the Decision Engine (§7) + Dependency Resolver (§8).
    This is the contract handed to the interoperability layer (§10).
    """
    required_services: list[str]
    reasoning: dict[str, str]
    execution_plan: list[ExecutionStep]


# ── Interview API models (§10) ───────────────────────────────────────────────

class QuestionOption(BaseModel):
    """A single option in an MCQ question."""
    label: str
    value: str


class InterviewQuestion(BaseModel):
    """A question to present to the user."""
    question_id: str
    question_text: str
    question_type: str = "mcq"  # "mcq" or "free_text"
    options: Optional[list[QuestionOption]] = None
    why: Optional[str] = None  # RAG-generated reason for asking


class InterviewMessageRequest(BaseModel):
    """Request body for POST /interview/message"""
    session_id: str
    user_response: Optional[str] = None  # None on first call to start interview


class InterviewMessageResponse(BaseModel):
    """Response body for POST /interview/message"""
    session_id: str
    state: InterviewState
    next_question: Optional[InterviewQuestion] = None
    profile_so_far: dict  # Partial or complete ProjectProfile as dict
    message: Optional[str] = None  # Greeting or status message
    profile_complete: bool = False

