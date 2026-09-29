"""
Integration tests for the RAG Intake & Decision Engine.

Tests the end-to-end interview flow:
1. Full interview with demo profile (chemical manufacturing, Pune)
2. Verifies the exact §13 expected output
3. Tests the decision endpoint
4. Tests a second profile (IT/Office) to verify skip logic

These tests use the interview engine directly (no HTTP server needed)
to keep them fast and dependency-light.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.interview.engine import process_message, get_decision
from app.interview.session import get_session_store


@pytest.fixture(autouse=True)
def clean_sessions():
    """Clear session store between tests."""
    store = get_session_store()
    store._sessions.clear()
    yield
    store._sessions.clear()


class TestFullInterviewChemicalManufacturing:
    """
    §13 demo profile: chemical manufacturing, Pune, land owned 7.5 ha,
    750 kW, industrial emissions + hazardous waste.

    Must produce the exact expected output.
    """

    def _run_full_interview(self, session_id: str = "test-chem-mfg") -> dict:
        """Run the full interview with the demo profile answers."""
        # Step 1: Start interview
        r = process_message(session_id)
        assert r["state"] == "IN_PROGRESS"
        assert r["next_question"] is not None

        # Answer sequence matching the question bank order
        answers = [
            ("MANUFACTURING", "project_type"),
            ("CHEMICAL", "industry_type"),
            ("Pune", "location_district"),
            ("true", "land_required"),
            ("Yes", "land_owned"),
            ("7.5", "land_area"),
            ("true", "electricity_required"),
            ("750", "electricity_load"),
            ("true", "industrial_emissions"),
            ("true", "hazardous_waste"),
        ]

        last_response = None
        for answer, expected_field in answers:
            r = process_message(session_id, answer)
            last_response = r
            if r.get("profile_complete"):
                break

        return last_response

    def test_profile_complete(self):
        result = self._run_full_interview()
        assert result["profile_complete"] is True

    def test_state_complete(self):
        result = self._run_full_interview()
        assert result["state"] == "COMPLETE"

    def test_all_three_services_required(self):
        result = self._run_full_interview()
        decision = result.get("decision", {})
        assert set(decision["required_services"]) == {
            "LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"
        }

    def test_reasoning_present(self):
        result = self._run_full_interview()
        decision = result.get("decision", {})
        assert "LAND_SERVICE" in decision["reasoning"]
        assert "ELECTRICITY_SERVICE" in decision["reasoning"]
        assert "POLLUTION_SERVICE" in decision["reasoning"]

    def test_execution_plan_wave_ordering(self):
        """
        §13: LAND_SERVICE and ELECTRICITY_SERVICE are wave 1 (parallel),
        POLLUTION_SERVICE is wave 2 depending on LAND_SERVICE.
        """
        result = self._run_full_interview()
        decision = result.get("decision", {})
        plan = decision["execution_plan"]

        wave_1 = [s for s in plan if s["wave"] == 1]
        wave_2 = [s for s in plan if s["wave"] == 2]

        # Wave 1: Land + Electricity
        wave_1_services = {s["service"] for s in wave_1}
        assert wave_1_services == {"LAND_SERVICE", "ELECTRICITY_SERVICE"}
        for s in wave_1:
            assert s["depends_on"] == []

        # Wave 2: Pollution
        assert len(wave_2) == 1
        assert wave_2[0]["service"] == "POLLUTION_SERVICE"
        assert wave_2[0]["depends_on"] == ["LAND_SERVICE"]

    def test_deterministic_repeated_runs(self):
        """§13: Must produce identical decision every time for identical profile."""
        result1 = self._run_full_interview("test-run-1")
        result2 = self._run_full_interview("test-run-2")

        d1 = result1["decision"]
        d2 = result2["decision"]

        assert d1["required_services"] == d2["required_services"]
        assert d1["reasoning"] == d2["reasoning"]
        assert len(d1["execution_plan"]) == len(d2["execution_plan"])
        for s1, s2 in zip(d1["execution_plan"], d2["execution_plan"]):
            assert s1["wave"] == s2["wave"]
            assert s1["service"] == s2["service"]
            assert s1["depends_on"] == s2["depends_on"]

    def test_decision_endpoint(self):
        """Test GET /interview/{session_id}/decision returns the same result."""
        self._run_full_interview("test-decision-ep")
        decision = get_decision("test-decision-ep")
        assert decision is not None
        assert set(decision["required_services"]) == {
            "LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"
        }

    def test_profile_content(self):
        """Verify the profile itself is correct."""
        result = self._run_full_interview()
        profile = result["profile_so_far"]
        assert profile["project_type"] == "MANUFACTURING"
        assert profile["industry_type"] == "CHEMICAL"
        assert profile["location"]["district"] == "Pune"
        assert profile["land"]["required"] is True
        assert profile["land"]["area_hectare"] == 7.5
        assert profile["electricity"]["required"] is True
        assert profile["electricity"]["required_load_kw"] == 750
        assert profile["environment"]["industrial_emissions"] is True
        assert profile["environment"]["hazardous_waste"] is True


class TestITOfficeSkipLogic:
    """
    Second profile: IT/Office in Mumbai, no emissions.
    Verifies that irrelevant questions are skipped (§13).
    """

    def _run_it_office_interview(self, session_id: str = "test-it-office") -> tuple[dict, int]:
        """Run interview with IT/Office answers. Returns (result, question_count)."""
        r = process_message(session_id)
        question_count = 0

        answers = {
            "project_type": "IT_OFFICE",
            "location_district": "Mumbai",
            "land_required": "true",
            "land_owned": "Yes",
            "land_area": "0.5",
            "electricity_required": "true",
            "electricity_load": "300",
            "industrial_emissions": "false",
            "hazardous_waste": "false",
        }

        last_response = r
        while not last_response.get("profile_complete", False):
            q = last_response.get("next_question")
            if q is None:
                break
            qid = q["question_id"]
            answer = answers.get(qid, "Other")
            last_response = process_message(session_id, answer)
            question_count += 1

        return last_response, question_count

    def test_skips_industry_type(self):
        """IT/Office should skip the industry_type question."""
        result, count = self._run_it_office_interview()
        assert result["profile_complete"] is True
        # industry_type should NOT be in the profile (it was skipped)
        assert result["profile_so_far"].get("industry_type") is None

    def test_no_pollution_service(self):
        """IT/Office with no emissions → no Pollution service."""
        result, _ = self._run_it_office_interview()
        decision = result.get("decision", {})
        assert "POLLUTION_SERVICE" not in decision["required_services"]
        assert set(decision["required_services"]) == {"LAND_SERVICE", "ELECTRICITY_SERVICE"}

    def test_all_wave_1(self):
        """Without Pollution, everything is wave 1."""
        result, _ = self._run_it_office_interview()
        decision = result.get("decision", {})
        for step in decision["execution_plan"]:
            assert step["wave"] == 1

    def test_fewer_questions_than_manufacturing(self):
        """IT/Office should ask fewer questions (industry_type skipped)."""
        result_it, count_it = self._run_it_office_interview("test-it-count")
        # Manufacturing asks all 10, IT/Office should ask 9 (skips industry_type)
        assert count_it < 10


class TestInterviewEdgeCases:
    """Edge cases and error handling."""

    def test_invalid_answer_reprompts(self):
        """§9: Invalid input should trigger re-prompt, not crash."""
        r = process_message("test-invalid")
        # Send a bogus answer
        r = process_message("test-invalid", "INVALID_PROJECT_TYPE_VALUE_123")
        assert r["state"] == "IN_PROGRESS"
        assert r.get("message") is not None
        assert "Invalid" in r["message"] or "invalid" in r["message"].lower()

    def test_completed_session_rejects_new_messages(self):
        """Completed sessions should return a message about being complete."""
        # Run a quick interview
        session_id = "test-completed"
        process_message(session_id)
        for answer in ["MANUFACTURING", "CHEMICAL", "Pune", "true", "Yes", "7.5",
                        "true", "750", "true", "true"]:
            r = process_message(session_id, answer)
            if r.get("profile_complete"):
                break

        # Try to send another message
        r = process_message(session_id, "more stuff")
        assert "complete" in r.get("message", "").lower()

    def test_nonexistent_session_decision(self):
        """Decision endpoint for nonexistent session returns None."""
        result = get_decision("nonexistent-session-id")
        assert result is None

    def test_incomplete_session_decision(self):
        """Decision endpoint for incomplete session returns None."""
        process_message("test-incomplete")
        result = get_decision("test-incomplete")
        assert result is None
