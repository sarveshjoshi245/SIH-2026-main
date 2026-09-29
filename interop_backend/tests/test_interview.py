import uuid


def _run_full_interview(client, session_id):
    """Drive the conversational interview to completion for a fixed profile:
    Manufacturing / Chemical / Pune / owns 7.5 Ha land / needs 300 kW power /
    has industrial emissions and hazardous waste.
    """
    answers = [
        None,           # start
        "MANUFACTURING",
        "CHEMICAL",
        "Pune",
        "true",         # land.required
        "Yes",          # land.ownership_status
        "7.5",          # land.area_hectare
        "true",         # electricity.required
        "300",          # electricity.required_load_kw
        "true",         # environment.industrial_emissions
        "true",         # environment.hazardous_waste
    ]

    result = None
    for answer in answers:
        result = client.post("/api/interview/message", json={
            "session_id": session_id,
            "user_response": answer,
        })
        assert result.status_code == 200

    return result.json()


def test_quick_decision_matches_full_interview_decision(client):
    session_id = f"consistency-test-{uuid.uuid4()}"
    final_response = _run_full_interview(client, session_id)
    assert final_response["profile_complete"] is True

    decision_res = client.get(f"/api/interview/{session_id}/decision")
    assert decision_res.status_code == 200
    interview_decision = decision_res.json()

    quick_res = client.post("/api/interview/quick-decision", json={
        "project_type": "MANUFACTURING",
        "industry_type": "CHEMICAL",
        "location": {"district": "Pune", "state": "Maharashtra"},
        "land": {
            "required": True,
            "owned": True,
            "ownership_status": "Yes",
            "area_hectare": 7.5
        },
        "electricity": {
            "required": True,
            "required_load_kw": 300
        },
        "environment": {
            "industrial_emissions": True,
            "hazardous_waste": True
        }
    })
    assert quick_res.status_code == 200
    quick_decision = quick_res.json()

    assert quick_decision["required_services"] == interview_decision["required_services"]
    assert quick_decision["reasoning"] == interview_decision["reasoning"]
    assert quick_decision["execution_plan"] == interview_decision["execution_plan"]

    # Sanity: both paths actually produced the full 3-department, 2-wave plan,
    # and Pollution's dependency reasoning (from dependency_resolver.py's
    # DEPENDENCY_REASONS) is present verbatim, not a placeholder.
    assert set(quick_decision["required_services"]) == {
        "LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"
    }
    pollution_step = next(
        s for s in quick_decision["execution_plan"] if s["service"] == "POLLUTION_SERVICE"
    )
    assert pollution_step["depends_on"] == ["LAND_SERVICE"]
    assert "verified Land Ownership Certificate" in pollution_step["reason"]


def test_quick_decision_skips_interview_session(client):
    # No session_id/interview state involved at all -- proves the endpoint
    # doesn't require going through the conversational flow.
    response = client.post("/api/interview/quick-decision", json={
        "project_type": "WAREHOUSE",
        "land": {"required": False},
        "electricity": {"required": True, "required_load_kw": 50},
        "environment": {"industrial_emissions": False, "hazardous_waste": False}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["required_services"] == ["ELECTRICITY_SERVICE"]
    assert data["execution_plan"][0]["service"] == "ELECTRICITY_SERVICE"
    assert data["execution_plan"][0]["depends_on"] == []
