"""
Static Question Bank & Skip Logic.

Defines all possible interview questions as MCQ-first (§4),
with skip conditions based on earlier answers, and fallback
question sets per project type for graceful degradation (§9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable

from app.models import ProjectProfile, QuestionOption


@dataclass
class QuestionDef:
    """Definition of an interview question."""
    question_id: str
    question_text: str
    question_type: str  # "mcq" or "free_text"
    options: list[dict] | None  # [{"label": "...", "value": "..."}]
    profile_field: str  # Dot-notation path into ProjectProfile (e.g., "land.area_hectare")
    skip_condition: Callable[[ProjectProfile], bool] | None = None  # Return True to skip
    default_why: str = ""  # Fallback "why" text if RAG retrieval fails


# ── Question Definitions ─────────────────────────────────────────────────────

QUESTION_BANK: list[QuestionDef] = [
    # Q1: Project type
    QuestionDef(
        question_id="project_type",
        question_text="What type of project are you establishing?",
        question_type="mcq",
        options=[
            {"label": "Manufacturing", "value": "MANUFACTURING"},
            {"label": "Warehouse", "value": "WAREHOUSE"},
            {"label": "IT/Office", "value": "IT_OFFICE"},
            {"label": "Other", "value": "OTHER"},
        ],
        profile_field="project_type",
        default_why="Different project types require different departmental verifications.",
    ),

    # Q2: Industry type (only relevant for manufacturing)
    QuestionDef(
        question_id="industry_type",
        question_text="What industry does your manufacturing project belong to?",
        question_type="mcq",
        options=[
            {"label": "Chemical", "value": "CHEMICAL"},
            {"label": "Pharmaceutical", "value": "PHARMACEUTICAL"},
            {"label": "Food Processing", "value": "FOOD_PROCESSING"},
            {"label": "Textile", "value": "TEXTILE"},
            {"label": "Electronics", "value": "ELECTRONICS"},
            {"label": "General", "value": "GENERAL"},
            {"label": "Other", "value": "OTHER"},
        ],
        profile_field="industry_type",
        skip_condition=lambda p: p.project_type is not None and p.project_type.value != "MANUFACTURING",
        default_why="Industry type determines which environmental and safety checks apply.",
    ),

    # Q3: Location — district
    QuestionDef(
        question_id="location_district",
        question_text="Where is the proposed project located?",
        question_type="mcq",
        options=[
            {"label": "Pune", "value": "Pune"},
            {"label": "Mumbai", "value": "Mumbai"},
            {"label": "Nashik", "value": "Nashik"},
            {"label": "Nagpur", "value": "Nagpur"},
            {"label": "Other", "value": "Other"},
        ],
        profile_field="location.district",
        default_why="Location determines which jurisdictional authorities handle verification.",
    ),

    # Q4: Land required?
    QuestionDef(
        question_id="land_required",
        question_text="Does your project require a specific land/site?",
        question_type="mcq",
        options=[
            {"label": "Yes", "value": "true"},
            {"label": "No", "value": "false"},
        ],
        profile_field="land.required",
        default_why="Land verification is needed if the project uses a specific physical site.",
    ),

    # Q5: Land ownership
    QuestionDef(
        question_id="land_owned",
        question_text="Do you already own the proposed land?",
        question_type="mcq",
        options=[
            {"label": "Yes", "value": "Yes"},
            {"label": "No", "value": "No"},
            {"label": "Under acquisition", "value": "Under acquisition"},
        ],
        profile_field="land.ownership_status",
        skip_condition=lambda p: p.land.required is False,
        default_why="Ownership status determines the type of land record verification needed.",
    ),

    # Q6: Land area
    QuestionDef(
        question_id="land_area",
        question_text="What is the approximate land requirement?",
        question_type="mcq",
        options=[
            {"label": "Less than 1 hectare", "value": "0.5"},
            {"label": "1–5 hectares", "value": "3.0"},
            {"label": "5–10 hectares", "value": "7.5"},
            {"label": "More than 10 hectares", "value": "15.0"},
        ],
        profile_field="land.area_hectare",
        skip_condition=lambda p: p.land.required is False,
        default_why="Land area determines which detailed verification checks are triggered.",
    ),

    # Q7: Electricity required?
    QuestionDef(
        question_id="electricity_required",
        question_text="Will your project require an electricity connection?",
        question_type="mcq",
        options=[
            {"label": "Yes", "value": "true"},
            {"label": "No", "value": "false"},
        ],
        profile_field="electricity.required",
        default_why="Electricity verification checks sanctioned load and connection status.",
    ),

    # Q8: Electricity load
    QuestionDef(
        question_id="electricity_load",
        question_text="What is your expected electricity requirement?",
        question_type="mcq",
        options=[
            {"label": "Less than 100 kW", "value": "50"},
            {"label": "100–500 kW", "value": "300"},
            {"label": "500 kW–1 MW", "value": "750"},
            {"label": "More than 1 MW", "value": "1500"},
        ],
        profile_field="electricity.required_load_kw",
        skip_condition=lambda p: p.electricity.required is False,
        default_why="Expected load determines whether detailed capacity checks are needed.",
    ),

    # Q9: Industrial emissions
    QuestionDef(
        question_id="industrial_emissions",
        question_text="Will the project generate industrial emissions, wastewater, or air pollutants?",
        question_type="mcq",
        options=[
            {"label": "Yes", "value": "true"},
            {"label": "No", "value": "false"},
            {"label": "Not sure", "value": "not_sure"},
        ],
        profile_field="environment.industrial_emissions",
        default_why="Industrial emissions trigger Pollution Control Board consent verification.",
    ),

    # Q10: Hazardous waste
    QuestionDef(
        question_id="hazardous_waste",
        question_text="Will the project generate or handle hazardous waste?",
        question_type="mcq",
        options=[
            {"label": "Yes", "value": "true"},
            {"label": "No", "value": "false"},
            {"label": "Not sure", "value": "not_sure"},
        ],
        profile_field="environment.hazardous_waste",
        default_why="Hazardous waste handling requires environmental consent verification.",
    ),
]


# ── Fallback question sets per project type (§9) ────────────────────────────

FALLBACK_QUESTIONS: dict[str, list[str]] = {
    "MANUFACTURING": [
        "project_type", "industry_type", "location_district",
        "land_required", "land_owned", "land_area",
        "electricity_required", "electricity_load",
        "industrial_emissions", "hazardous_waste",
    ],
    "WAREHOUSE": [
        "project_type", "location_district",
        "land_required", "land_owned", "land_area",
        "electricity_required", "electricity_load",
        "industrial_emissions", "hazardous_waste",
    ],
    "IT_OFFICE": [
        "project_type", "location_district",
        "land_required", "land_area",
        "electricity_required", "electricity_load",
        "industrial_emissions", "hazardous_waste",
    ],
    "OTHER": [
        "project_type", "location_district",
        "land_required", "land_area",
        "electricity_required", "electricity_load",
        "industrial_emissions", "hazardous_waste",
    ],
    "DEFAULT": [
        "project_type", "location_district",
        "land_required", "land_owned", "land_area",
        "electricity_required", "electricity_load",
        "industrial_emissions", "hazardous_waste",
    ],
}


def get_question_by_id(question_id: str) -> QuestionDef | None:
    """Look up a question definition by its ID."""
    for q in QUESTION_BANK:
        if q.question_id == question_id:
            return q
    return None


def should_skip_question(question: QuestionDef, profile: ProjectProfile) -> bool:
    """
    Determine if a question should be skipped based on the current profile state.

    Returns True if the question should be skipped, False if it should be asked.
    """
    if question.skip_condition is None:
        return False

    try:
        return question.skip_condition(profile)
    except Exception:
        # If skip evaluation fails, don't skip — ask the question (§9: don't crash)
        return False


def get_next_question(
    profile: ProjectProfile,
    answered_ids: set[str],
) -> QuestionDef | None:
    """
    Get the next unanswered, non-skipped question for the current profile state.

    Returns None if all questions have been asked or skipped.
    """
    for question in QUESTION_BANK:
        if question.question_id in answered_ids:
            continue
        if should_skip_question(question, profile):
            continue
        return question
    return None


def get_fallback_question_ids(project_type: str | None) -> list[str]:
    """Get the fallback question list for a project type (§9)."""
    if project_type and project_type in FALLBACK_QUESTIONS:
        return FALLBACK_QUESTIONS[project_type]
    return FALLBACK_QUESTIONS["DEFAULT"]
