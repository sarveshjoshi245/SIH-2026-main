def test_admin_set_state_valid_transition(client, admin_headers, interop_headers):
    headers_bypass = {**interop_headers, "X-Bypass-Chaos": "true"}

    # 1. Check initial status
    initial_res = client.get("/api/electricity/status/ELEC-2026-00102", headers=headers_bypass)
    assert initial_res.status_code == 200
    assert initial_res.json()["application_status"] == "PENDING"

    # 2. Mutate state via admin endpoint
    mutation_payload = {
        "application_number": "ELEC-2026-00102",
        "application_status": "APPROVED",
        "inspection_status": "COMPLETED",
        "meter_status": "INSTALLED",
        "connection_status": "ENERGIZED",
        "security_deposit_status": "PAID"
    }
    mutate_res = client.post("/api/admin/set-state", json=mutation_payload, headers=admin_headers)
    assert mutate_res.status_code == 200
    assert mutate_res.json()["status"] == "SUCCESS"

    # 3. Verify status endpoint reflects updated state
    status_res = client.get("/api/electricity/status/ELEC-2026-00102", headers=headers_bypass)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["application_status"] == "APPROVED"
    assert status_data["inspection_status"] == "COMPLETED"
    assert status_data["meter_status"] == "INSTALLED"
    assert status_data["connection_status"] == "ENERGIZED"
    assert status_data["retryable"] is False

    # 4. Verify /verify endpoint reflects updated state
    verify_payload = {
        "application_number": "ELEC-2026-00102",
        "pan": "FGHIJ5678K"
    }
    verify_res = client.post("/api/electricity/verify", json=verify_payload, headers=headers_bypass)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["pan_match"] is True
    assert verify_data["application"]["appl_stat"] == "APPROVED"
    assert verify_data["application"]["conn_stat"] == "ENERGIZED"


def test_admin_set_state_invalid_status_rejected_422(client, admin_headers):
    mutation_payload = {
        "application_number": "ELEC-2026-00102",
        "application_status": "COMPLETELY_INVALID_STATUS"
    }
    res = client.post("/api/admin/set-state", json=mutation_payload, headers=admin_headers)
    assert res.status_code == 422
    data = res.json()
    assert data["status"] == "INVALID_STATE_TRANSITION"


def test_audit_log_created_and_accessible(client, interop_headers):
    # Call verify to generate audit
    headers_bypass = {**interop_headers, "X-Bypass-Chaos": "true"}
    client.post(
        "/api/electricity/verify",
        json={"application_number": "ELEC-2026-00101", "pan": "ABCDE1234F"},
        headers=headers_bypass
    )

    # Check audit log endpoint
    audit_res = client.get("/api/audit?application_number=ELEC-2026-00101", headers=interop_headers)
    assert audit_res.status_code == 200
    audit_list = audit_res.json()
    assert len(audit_list) > 0
    latest = audit_list[0]
    assert latest["application_number"] == "ELEC-2026-00101"
    assert latest["outcome"] == "SUCCESS"
    assert latest["response_code"] == 200
    assert latest["transaction_id"].startswith("ELEC-")
