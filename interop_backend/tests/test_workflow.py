def test_plant_verification_success(client, abc_headers):
    payload = {
        "project_name": "ABC Chakan Expansion Unit",
        "organization_pan": "ABCDE1234F",
        "land_survey_number": "101",
        "electricity_application_number": "ELEC-2026-00101",
        "pollution_application_number": "MPCB-8821",
        "industry_type": "Chemical"
    }
    response = client.post("/api/projects/verify-plant", json=payload, headers=abc_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_pan"] == "ABCDE1234F"
    assert data["pan_identity_verified"] is True
    assert data["overall_clearance_status"] == "RESOLVED"
    assert len(data["department_checks"]) == 3
    assert data["transaction_id"].startswith("TXN-")


def test_plant_verification_waiting(client, abc_token):
    # XYZ Manufacturing token
    from app.auth.jwt_handler import create_access_token
    xyz_token = create_access_token({
        "sub": "applicant@xyzmfg.com",
        "pan": "FGHIJ5678K",
        "org": "XYZ Manufacturing Pvt Ltd"
    })
    headers = {"Authorization": f"Bearer {xyz_token}"}

    payload = {
        "project_name": "XYZ Talegaon Unit",
        "organization_pan": "FGHIJ5678K",
        "land_survey_number": "103",
        "electricity_application_number": "ELEC-2026-00102",
        "pollution_application_number": "MPCB-8822"
    }
    response = client.post("/api/projects/verify-plant", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organization_pan"] == "FGHIJ5678K"
    assert data["pan_identity_verified"] is True
    assert data["overall_clearance_status"] == "WAITING"
    assert "polling" in data["recommended_next_action"].lower()


def test_pollution_not_dispatched_when_land_pending(client, abc_token):
    # Guards the MPCB dependency guarantee: Pollution must only be dispatched
    # once Land (and Electricity) are FULLY approved, not merely on file.
    # Survey "103" mocks Land with mutation_status "PENDING" -- a record
    # exists but isn't approved -- so the Pollution adapter must never be
    # called for this request.
    from app.auth.jwt_handler import create_access_token
    xyz_token = create_access_token({
        "sub": "applicant@xyzmfg.com",
        "pan": "FGHIJ5678K",
        "org": "XYZ Manufacturing Pvt Ltd"
    })
    headers = {"Authorization": f"Bearer {xyz_token}"}

    payload = {
        "project_name": "XYZ Talegaon Unit",
        "organization_pan": "FGHIJ5678K",
        "land_survey_number": "103",
        "electricity_application_number": "ELEC-2026-00102",
        "pollution_application_number": "MPCB-8822"
    }
    response = client.post("/api/projects/verify-plant", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    pollution_check = next(c for c in data["department_checks"] if c["department"] == "POLLUTION")
    assert pollution_check["status"] == "UNAVAILABLE"
    assert pollution_check["raw_facts"] is None
    assert pollution_check["error"] is not None
    assert "blocked" in pollution_check["error"].lower()
    assert "LAND" in pollution_check["error"]


def test_transaction_detail_endpoint(client, abc_headers):
    # Run a verify first
    payload = {
        "project_name": "ABC Chakan Expansion Unit",
        "organization_pan": "ABCDE1234F",
        "land_survey_number": "101",
        "electricity_application_number": "ELEC-2026-00101",
        "pollution_application_number": "MPCB-8821"
    }
    verify_res = client.post("/api/projects/verify-plant", json=payload, headers=abc_headers)
    txn_id = verify_res.json()["transaction_id"]

    # Fetch detail
    detail_res = client.get(f"/api/projects/transactions/{txn_id}", headers=abc_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["transaction_id"] == txn_id
    assert len(detail["department_executions"]) == 3
