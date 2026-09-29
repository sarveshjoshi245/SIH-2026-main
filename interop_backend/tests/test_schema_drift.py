def test_schema_drift_detection(client):
    payload = {
        "department_code": "ELECTRICITY",
        "sample_payload": {
            "application_no": "ELEC-2026-00101",
            "approved_load": "500",  # Mutated field
            "power_status": "ENERGIZED"  # Mutated field
        }
    }
    response = client.post("/api/schema/detect", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_drift"] is True
    assert "approved_load" in data["unmapped_fields"]
    assert len(data["suggestions"]) > 0
    sug = next(s for s in data["suggestions"] if s["detected_field"] == "approved_load")
    assert sug["suggested_canonical_field"] == "sanctioned_load_kw"
    assert sug["confidence_score"] >= 0.70


def test_schema_drift_approval(client, admin_headers):
    payload = {
        "department_code": "ELECTRICITY",
        "source_field": "approved_load",
        "target_canonical_field": "sanctioned_load_kw"
    }
    response = client.post("/api/schema/approve-drift", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"


def test_schema_drift_approval_rejects_non_admin(client, abc_headers):
    # ABC Industries is a regular APPLICANT user, not an ADMIN -- approving
    # schema mappings must stay a government-admin-only action.
    payload = {
        "department_code": "ELECTRICITY",
        "source_field": "approved_load",
        "target_canonical_field": "sanctioned_load_kw"
    }
    response = client.post("/api/schema/approve-drift", json=payload, headers=abc_headers)
    assert response.status_code == 403


def test_approved_mapping_is_applied_at_transform_time(client, admin_headers):
    # Core adaptability claim: a department can rename a field, and once an
    # admin approves the new mapping, the canonical transform picks it up
    # immediately -- no code change or redeploy. "pan_reference" is not in
    # LAND_DIRECT_MAP, so this only works if the DB-approved rule is consulted.
    raw_payload = {
        "gtn": "202",
        "owner_name": "Delta Fabrication Pvt Ltd",
        "pan_reference": "DELTA5678Z",
        "mutation_status": "APPROVED",
    }

    # Before approval: the renamed field is unmapped, so organization_pan is blank.
    before = client.post("/api/canonical/transform", json={
        "department": "LAND",
        "raw_payload": raw_payload,
        "requested_pan": "DELTA5678Z"
    })
    assert before.status_code == 200
    assert before.json()["organization_pan"] == ""

    approve = client.post("/api/schema/approve-drift", json={
        "department_code": "LAND",
        "source_field": "pan_reference",
        "target_canonical_field": "organization_pan"
    }, headers=admin_headers)
    assert approve.status_code == 200

    # After approval: the same raw payload now maps pan_reference -> organization_pan.
    after = client.post("/api/canonical/transform", json={
        "department": "LAND",
        "raw_payload": raw_payload,
        "requested_pan": "DELTA5678Z"
    })
    assert after.status_code == 200
    after_data = after.json()
    assert after_data["organization_pan"] == "DELTA5678Z"
    assert after_data["land_details"]["ownership_status"] == "VALID"
