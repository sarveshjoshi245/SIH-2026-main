"""
Unit tests for the Deterministic Dependency Resolver (§8).

Tests wave ordering correctness per §14 step 1:
1. All 3 services → Land+Electricity wave 1, Pollution wave 2
2. Land + Electricity only → both wave 1
3. Pollution only (no Land) → Pollution wave 1 (dependency doesn't apply)
4. Single service → wave 1
5. Determinism check — identical output on repeated runs
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.dependency_resolver import resolve_execution_order, SERVICE_DEPENDENCIES


class TestAllThreeServices:
    """When all 3 services are required, Pollution must wait for Land."""

    @pytest.fixture
    def plan(self):
        return resolve_execution_order(["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"])

    def test_three_steps(self, plan):
        assert len(plan) == 3

    def test_land_wave_1(self, plan):
        land = next(s for s in plan if s.service == "LAND_SERVICE")
        assert land.wave == 1
        assert land.depends_on == []

    def test_electricity_wave_1(self, plan):
        elec = next(s for s in plan if s.service == "ELECTRICITY_SERVICE")
        assert elec.wave == 1
        assert elec.depends_on == []

    def test_pollution_wave_2(self, plan):
        poll = next(s for s in plan if s.service == "POLLUTION_SERVICE")
        assert poll.wave == 2
        assert poll.depends_on == ["LAND_SERVICE"]

    def test_pollution_reason_mentions_land(self, plan):
        poll = next(s for s in plan if s.service == "POLLUTION_SERVICE")
        assert "Land Ownership Certificate" in poll.reason

    def test_wave_1_before_wave_2(self, plan):
        """Ensure wave ordering is correct in list order."""
        waves = [s.wave for s in plan]
        assert waves == sorted(waves)


class TestLandAndElectricityOnly:
    """Without Pollution, both services are wave 1."""

    @pytest.fixture
    def plan(self):
        return resolve_execution_order(["LAND_SERVICE", "ELECTRICITY_SERVICE"])

    def test_two_steps(self, plan):
        assert len(plan) == 2

    def test_both_wave_1(self, plan):
        for step in plan:
            assert step.wave == 1
            assert step.depends_on == []


class TestPollutionOnlyNoDependency:
    """
    If only Pollution is required (Land is NOT required),
    the dependency doesn't apply — Pollution goes to wave 1.
    """

    @pytest.fixture
    def plan(self):
        return resolve_execution_order(["POLLUTION_SERVICE"])

    def test_single_step(self, plan):
        assert len(plan) == 1

    def test_pollution_wave_1(self, plan):
        assert plan[0].wave == 1
        assert plan[0].service == "POLLUTION_SERVICE"
        assert plan[0].depends_on == []


class TestSingleService:
    """Any single service should be wave 1."""

    @pytest.mark.parametrize("service", ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"])
    def test_single_service_wave_1(self, service):
        plan = resolve_execution_order([service])
        assert len(plan) == 1
        assert plan[0].wave == 1
        assert plan[0].depends_on == []


class TestLandAndPollution:
    """Land + Pollution (no Electricity): Land wave 1, Pollution wave 2."""

    @pytest.fixture
    def plan(self):
        return resolve_execution_order(["LAND_SERVICE", "POLLUTION_SERVICE"])

    def test_land_wave_1(self, plan):
        land = next(s for s in plan if s.service == "LAND_SERVICE")
        assert land.wave == 1

    def test_pollution_wave_2(self, plan):
        poll = next(s for s in plan if s.service == "POLLUTION_SERVICE")
        assert poll.wave == 2
        assert poll.depends_on == ["LAND_SERVICE"]


class TestDeterminism:
    """§13: Must produce identical results on repeated runs."""

    def test_repeated_runs_identical(self):
        services = ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"]
        plan1 = resolve_execution_order(services)
        plan2 = resolve_execution_order(services)
        assert len(plan1) == len(plan2)
        for s1, s2 in zip(plan1, plan2):
            assert s1.wave == s2.wave
            assert s1.service == s2.service
            assert s1.depends_on == s2.depends_on
            assert s1.reason == s2.reason


class TestEmptyServices:
    """Edge case: no services required."""

    def test_empty_input(self):
        plan = resolve_execution_order([])
        assert plan == []


class TestUnknownServiceFallback:
    """§9: Unknown service not in SERVICE_DEPENDENCIES defaults to no deps."""

    def test_unknown_service_no_crash(self):
        plan = resolve_execution_order(["LAND_SERVICE", "UNKNOWN_SERVICE"])
        assert len(plan) == 2
        unknown = next(s for s in plan if s.service == "UNKNOWN_SERVICE")
        assert unknown.wave == 1
        assert unknown.depends_on == []
