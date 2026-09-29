def test_audit_log_records_masked_pan(client, abc_headers):
    # Perform a plant verification
    payload = {
        "project_name": "ABC Chakan Expansion Unit",
        "organization_pan": "ABCDE1234F",
        "land_survey_number": "101",
        "electricity_application_number": "ELEC-2026-00101",
        "pollution_application_number": "MPCB-8821"
    }
    client.post("/api/projects/verify-plant", json=payload, headers=abc_headers)

    # Fetch audit logs
    res = client.get("/api/audit", headers=abc_headers)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0
    latest = logs[0]
    assert latest["action"] == "VERIFY_PLANT_CLEARANCE"
    assert latest["masked_pan"] == "AB****34F"
    assert "ABCDE1234F" not in latest["masked_pan"]
