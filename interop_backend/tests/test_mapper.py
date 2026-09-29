def test_transform_land_payload(client):
    raw_land = {
        "gtn": "101",
        "malak_name": "ABC Industries Pvt Ltd",
        "malak_pan": "ABCDE1234F",
        "kshetra": 4.5,
        "kshetra_unit": "HECTARES",
        "jamabandi": "APPROVED",
        "jamin_prakar": "INDUSTRIAL",
        "bandhak": False,
        "court_case": False,
        "district": "Pune",
        "taluka": "Khed",
        "village": "Chakan"
    }
    response = client.post("/api/canonical/transform", json={
        "department": "LAND",
        "raw_payload": raw_land,
        "requested_pan": "ABCDE1234F"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["organization_pan"] == "ABCDE1234F"
    assert data["organization_name"] == "ABC Industries Pvt Ltd"
    assert data["land_details"]["survey_number"] == "101"
    assert data["land_details"]["area"] == 4.5
    assert data["land_details"]["mutation_status"] == "APPROVED"
    assert data["land_details"]["ownership_status"] == "VALID"
    assert data["status"] == "RESOLVED"


def test_transform_electricity_payload(client):
    raw_elec = {
        "appl_no": "ELEC-2026-00101",
        "cust_name": "ABC Industries Pvt Ltd",
        "cust_pan": "ABCDE1234F",
        "load_req": "500",
        "load_sanc": "500",
        "cat_code": "HT-IND",
        "appl_stat": "APPROVED",
        "insp_stat": "COMPLETED",
        "meter_stat": "INSTALLED",
        "conn_stat": "ENERGIZED",
        "dues_flag": False
    }
    response = client.post("/api/canonical/transform", json={
        "department": "ELECTRICITY",
        "raw_payload": raw_elec,
        "requested_pan": "ABCDE1234F"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["organization_pan"] == "ABCDE1234F"
    assert data["industry_type"] == "INDUSTRIAL"
    assert data["electricity_details"]["requested_load_kw"] == 500.0
    assert data["electricity_details"]["sanctioned_load_kw"] == 500.0
    assert data["electricity_details"]["outstanding_dues"] is False
    assert data["status"] == "RESOLVED"


def test_transform_pollution_payload(client):
    raw_poll = {
        "application_no": "MPCB-8821",
        "application_project_id": "PROJ-101",
        "industry_name": "ABC Industries Pvt Ltd",
        "industry_pan": "ABCDE1234F",
        "consent_type": "CTE",
        "consent_status": "APPROVED",
        "compliance_status": "COMPLIANT",
        "region": "Pune",
        "plant_location": "MIDC Pune",
        "industry_type": "Chemical"
    }
    response = client.post("/api/canonical/transform", json={
        "department": "POLLUTION",
        "raw_payload": raw_poll,
        "requested_pan": "ABCDE1234F"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["organization_pan"] == "ABCDE1234F"
    assert data["pollution_details"]["consent_status"] == "APPROVED"
    assert data["pollution_details"]["compliance_status"] == "COMPLIANT"
    assert data["status"] == "RESOLVED"

def test_transform_land_payload_actual_shape(client, admin_headers):
    # This fixture represents the ACTUAL shape returned by the land_api today,
    # which drift-mutated from 'malak_pan' -> 'organization_pan' and 'malak_name' -> 'owner'.
    raw_land = {
        "survey_number": "101",
        "canonical": {
            "survey_number": "101",
            "owner": "ABC Industries Pvt Ltd",
            "organization_pan": "ABCDE1234F",
            "area_hectares": "8.0",
            "area_unit": "HA",
            "mutation_status": "APPROVED",
            "land_type": "INDUSTRIAL",
            "encumbrance": False,
            "court_case": False,
            "district": "Pune",
            "taluka": "Haveli",
            "village": "Wagholi"
        }
    }
    
    # 1. Before approval, it fails to map pan and owner
    res_before = client.post("/api/canonical/transform", json={
        "department": "LAND",
        "raw_payload": raw_land,
        "requested_pan": "ABCDE1234F"
    })
    data_before = res_before.json()
    assert data_before.get("organization_pan") == "", "Should be unmapped before approval"
    assert data_before.get("organization_name") == "", "Should be unmapped before approval"
    
    # 2. Admin approves the schema drift mappings
    client.post("/api/schema/approve-drift", json={
        "department_code": "LAND",
        "source_field": "owner",
        "target_canonical_field": "organization_name"
    }, headers=admin_headers)
    
    client.post("/api/schema/approve-drift", json={
        "department_code": "LAND",
        "source_field": "organization_pan",
        "target_canonical_field": "organization_pan"
    }, headers=admin_headers)
    
    client.post("/api/schema/approve-drift", json={
        "department_code": "LAND",
        "source_field": "survey_number",
        "target_canonical_field": "land_details.survey_number"
    }, headers=admin_headers)
    
    # 3. After approval, the transform should succeed dynamically
    res_after = client.post("/api/canonical/transform", json={
        "department": "LAND",
        "raw_payload": raw_land,
        "requested_pan": "ABCDE1234F"
    })
    data_after = res_after.json()
    assert data_after["organization_pan"] == "ABCDE1234F"
    assert data_after["organization_name"] == "ABC Industries Pvt Ltd"
    assert data_after["land_details"]["survey_number"] == "101"
    assert data_after["land_details"]["area"] == 8.0
    assert data_after["land_details"]["ownership_status"] == "VALID"
    assert data_after["status"] == "RESOLVED"
