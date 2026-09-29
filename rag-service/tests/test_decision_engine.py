"""
Unit tests for the Deterministic Decision Engine (§7).

Tests 4 hand-written profiles per §14 step 1:
1. Chemical manufacturing → all 3 services
2. IT/Office with no emissions → Land + Electricity only
3. Warehouse with hazardous materials → all 3 services
4. Minimal project (electricity only) → Electricity only
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import (
    ProjectProfile, ProjectType, IndustryType,
    LocationInfo, LandInfo, ElectricityInfo, EnvironmentInfo,
)
from app.decision_engine import decide_required_services


class TestDecisionEngineChemicalManufacturing:
    """Profile 1: Chemical manufacturing in Pune — all 3 services required."""

    @pytest.fixture
    def profile(self) -> ProjectProfile:
        return ProjectProfile(
            project_type=ProjectType.MANUFACTURING,
            industry_type=IndustryType.CHEMICAL,
            location=LocationInfo(district="Pune", state="Maharashtra"),
            land=LandInfo(required=True, owned=True, area_hectare=7.5),
            electricity=ElectricityInfo(required=True, required_load_kw=750),
            environment=EnvironmentInfo(industrial_emissions=True, hazardous_waste=True),
        )

    def test_all_three_services_required(self, profile: ProjectProfile):
        services, reasoning = decide_required_services(profile)
        assert set(services) == {"LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"}

    def test_land_reasoning_includes_area(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "7.5" in reasoning["LAND_SERVICE"]

    def test_electricity_reasoning_includes_load(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "750" in reasoning["ELECTRICITY_SERVICE"]

    def test_pollution_reasoning_includes_both(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "emissions" in reasoning["POLLUTION_SERVICE"]
        assert "hazardous waste" in reasoning["POLLUTION_SERVICE"]

    def test_deterministic_output(self, profile: ProjectProfile):
        """§13: Must produce identical output every time for identical profile."""
        result1 = decide_required_services(profile)
        result2 = decide_required_services(profile)
        assert result1 == result2


class TestDecisionEngineITOffice:
    """Profile 2: IT/Office with no emissions — Land + Electricity only."""

    @pytest.fixture
    def profile(self) -> ProjectProfile:
        return ProjectProfile(
            project_type=ProjectType.IT_OFFICE,
            industry_type=IndustryType.GENERAL,
            location=LocationInfo(district="Mumbai", state="Maharashtra"),
            land=LandInfo(required=True, owned=True, area_hectare=0.5),
            electricity=ElectricityInfo(required=True, required_load_kw=200),
            environment=EnvironmentInfo(industrial_emissions=False, hazardous_waste=False),
        )

    def test_only_land_and_electricity(self, profile: ProjectProfile):
        services, _ = decide_required_services(profile)
        assert set(services) == {"LAND_SERVICE", "ELECTRICITY_SERVICE"}
        assert "POLLUTION_SERVICE" not in services

    def test_no_pollution_reasoning(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "POLLUTION_SERVICE" not in reasoning


class TestDecisionEngineWarehouseHazardous:
    """Profile 3: Warehouse with hazardous materials — all 3 services."""

    @pytest.fixture
    def profile(self) -> ProjectProfile:
        return ProjectProfile(
            project_type=ProjectType.WAREHOUSE,
            industry_type=IndustryType.GENERAL,
            location=LocationInfo(district="Nashik", state="Maharashtra"),
            land=LandInfo(required=True, owned=False, area_hectare=3.0),
            electricity=ElectricityInfo(required=True, required_load_kw=150),
            environment=EnvironmentInfo(industrial_emissions=False, hazardous_waste=True),
        )

    def test_all_three_services(self, profile: ProjectProfile):
        services, _ = decide_required_services(profile)
        assert set(services) == {"LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"}

    def test_pollution_only_mentions_hazardous(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "hazardous waste" in reasoning["POLLUTION_SERVICE"]
        # emissions is False, so should not be mentioned
        assert "emissions" not in reasoning["POLLUTION_SERVICE"]


class TestDecisionEngineMinimalElectricityOnly:
    """Profile 4: Minimal project — only electricity required."""

    @pytest.fixture
    def profile(self) -> ProjectProfile:
        return ProjectProfile(
            project_type=ProjectType.OTHER,
            location=LocationInfo(district="Pune", state="Maharashtra"),
            land=LandInfo(required=False),
            electricity=ElectricityInfo(required=True, required_load_kw=50),
            environment=EnvironmentInfo(industrial_emissions=False, hazardous_waste=False),
        )

    def test_only_electricity(self, profile: ProjectProfile):
        services, _ = decide_required_services(profile)
        assert services == ["ELECTRICITY_SERVICE"]

    def test_no_land_or_pollution(self, profile: ProjectProfile):
        _, reasoning = decide_required_services(profile)
        assert "LAND_SERVICE" not in reasoning
        assert "POLLUTION_SERVICE" not in reasoning


class TestDecisionEngineEdgeCases:
    """Edge cases for robustness."""

    def test_electricity_by_load_only(self):
        """Electricity required when load > 0 even if required is not explicitly True."""
        profile = ProjectProfile(
            project_type=ProjectType.MANUFACTURING,
            location=LocationInfo(district="Pune"),
            land=LandInfo(required=False),
            electricity=ElectricityInfo(required=False, required_load_kw=500),
            environment=EnvironmentInfo(industrial_emissions=False, hazardous_waste=False),
        )
        services, _ = decide_required_services(profile)
        assert "ELECTRICITY_SERVICE" in services

    def test_no_services_required(self):
        """A profile where nothing is required."""
        profile = ProjectProfile(
            project_type=ProjectType.OTHER,
            location=LocationInfo(district="Pune"),
            land=LandInfo(required=False),
            electricity=ElectricityInfo(required=False, required_load_kw=0),
            environment=EnvironmentInfo(industrial_emissions=False, hazardous_waste=False),
        )
        services, reasoning = decide_required_services(profile)
        assert services == []
        assert reasoning == {}
