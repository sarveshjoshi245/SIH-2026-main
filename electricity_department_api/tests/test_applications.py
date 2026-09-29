def test_get_existing_application_200(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    response = client.get("/api/electricity/applications/ELEC-2026-00101", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["appl_no"] == "ELEC-2026-00101"
    assert data["cust_name"] == "ABC Industries Pvt Ltd"
    assert data["cust_pan"] == "ABCDE1234F"
    assert data["load_sanc"] == "500"
    assert data["load_sanc_unit"] == "KW"
    assert data["appl_stat"] == "APPROVED"
    assert data["insp_stat"] == "COMPLETED"
    assert data["meter_stat"] == "INSTALLED"
    assert data["conn_stat"] == "ENERGIZED"
    assert data["dues_flag"] is False


def test_get_non_existing_application_404(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    response = client.get("/api/electricity/applications/ELEC-999999", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "NOT_FOUND"
    assert data["department"] == "ELECTRICITY_DISTRIBUTION"
    assert data["application_number"] == "ELEC-999999"


def test_schema_drift_only_changes_field_names(client, interop_headers):
    # Pass header to force schema drift
    headers = {**interop_headers, "X-Bypass-Chaos": "true", "X-Force-Schema-Drift": "true"}
    response = client.get("/api/electricity/applications/ELEC-2026-00101", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Drifted keys should exist
    assert "application_no" in data
    assert "consumer_name" in data
    assert "sanctioned_load" in data
    assert "application_status" in data

    # Values must remain identical and uncorrupted
    assert data["application_no"] == "ELEC-2026-00101"
    assert data["consumer_name"] == "ABC Industries Pvt Ltd"
    assert data["sanctioned_load"] == "500"
    assert data["application_status"] == "APPROVED"
