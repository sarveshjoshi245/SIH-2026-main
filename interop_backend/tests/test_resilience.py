from app.engine.circuit_breaker import CircuitBreaker, CircuitOpenException


def test_circuit_breaker_lifecycle():
    cb = CircuitBreaker(failure_threshold=2, recovery_time_sec=1)
    assert cb.state == "CLOSED"

    # Record 1 failure -> still CLOSED
    cb.record_failure()
    assert cb.state == "CLOSED"

    # Record 2nd failure -> transitions to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"

    # Before call should raise CircuitOpenException
    try:
        cb.before_call("TEST_SERVICE")
        assert False, "Expected CircuitOpenException"
    except CircuitOpenException as e:
        assert e.service_name == "TEST_SERVICE"

    # Record success resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"


def test_partial_outage_handling_does_not_crash_workflow(client, abc_headers):
    # Survey 999 simulates an outage in Land department
    payload = {
        "project_name": "ABC Chakan Expansion Unit",
        "organization_pan": "ABCDE1234F",
        "land_survey_number": "999",  # Land outage
        "electricity_application_number": "ELEC-2026-00101",
        "pollution_application_number": "MPCB-8821"
    }
    response = client.post("/api/projects/verify-plant", json=payload, headers=abc_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_clearance_status"] in ["ACTION_REQUIRED", "FAILED"]
    land_check = next(c for c in data["department_checks"] if c["department"] == "LAND")
    assert land_check["status"] == "UNAVAILABLE"
