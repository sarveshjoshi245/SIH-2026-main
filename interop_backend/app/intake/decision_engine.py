"""
Deterministic Decision Engine (§7).

Takes a validated ProjectProfile and deterministically decides which
departmental services are required, with a one-line reason for each.

NO LLM in the loop — pure rule-based logic.
"""

from __future__ import annotations

from app.intake.models import ProjectProfile


def decide_required_services(profile: ProjectProfile) -> tuple[list[str], dict[str, str]]:
    """
    Apply deterministic rules from §7 to determine which services are required.

    Args:
        profile: A validated ProjectProfile.

    Returns:
        A tuple of (required_services list, reasoning dict).
        - required_services: e.g. ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"]
        - reasoning: e.g. {"LAND_SERVICE": "Project requires land area of 7.5 hectares"}
    """
    required_services: list[str] = []
    reasoning: dict[str, str] = {}

    # Rule 1: Land service
    if profile.land.required is True:
        required_services.append("LAND_SERVICE")
        # Build a descriptive reason
        area_part = ""
        if profile.land.area_hectare is not None and profile.land.area_hectare > 0:
            area_part = f" of {profile.land.area_hectare} hectares"
        reasoning["LAND_SERVICE"] = f"Project requires land area{area_part}"

    # Rule 2: Electricity service
    if (
        profile.electricity.required is True
        or (profile.electricity.required_load_kw is not None and profile.electricity.required_load_kw > 0)
    ):
        required_services.append("ELECTRICITY_SERVICE")
        load_part = ""
        if profile.electricity.required_load_kw is not None and profile.electricity.required_load_kw > 0:
            load_part = f" {profile.electricity.required_load_kw} kW power connection"
        reasoning["ELECTRICITY_SERVICE"] = f"Project requires{load_part}" if load_part else "Project requires electricity connection"

    # Rule 3: Pollution service
    if (
        profile.environment.industrial_emissions is True
        or profile.environment.hazardous_waste is True
    ):
        required_services.append("POLLUTION_SERVICE")
        parts = []
        if profile.environment.industrial_emissions is True:
            parts.append("industrial emissions")
        if profile.environment.hazardous_waste is True:
            parts.append("hazardous waste")
        reasoning["POLLUTION_SERVICE"] = f"Project generates {' and '.join(parts)}"

    return required_services, reasoning

