def test_verify_correct_pan_matches(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    payload = {
        "application_number": "ELEC-2026-00101",
        "pan": "ABCDE1234F"
    }
    response = client.post("/api/electricity/verify", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["pan_match"] is True
    assert data["application"]["appl_no"] == "ELEC-2026-00101"
    assert data["application"]["appl_stat"] == "APPROVED"
    assert data["transaction_id"].startswith("ELEC-")


def test_verify_wrong_pan_returns_200_with_pan_match_false(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    payload = {
        "application_number": "ELEC-2026-00101",
        "pan": "ZZZZZ9999Z"  # Wrong PAN
    }
    response = client.post("/api/electricity/verify", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["pan_match"] is False
    assert data["application"]["appl_no"] == "ELEC-2026-00101"


def test_verify_non_existing_application_404(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    payload = {
        "application_number": "ELEC-2026-99999",
        "pan": "ABCDE1234F"
    }
    response = client.post("/api/electricity/verify", json=payload, headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "NOT_FOUND"


def test_verify_rejected_application_returns_reason(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    payload = {
        "application_number": "ELEC-2026-00104",
        "pan": "RSTUV3456W"
    }
    response = client.post("/api/electricity/verify", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["pan_match"] is True
    assert data["application"]["appl_stat"] == "REJECTED"
    assert data["application"]["insp_stat"] == "FAILED"
    assert data["application"]["rej_reason"] == "Electrical infrastructure inspection failed"


def test_verify_dues_application_returns_dues_flag(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    payload = {
        "application_number": "ELEC-2026-00105",
        "pan": "ABCDE1234F"
    }
    response = client.post("/api/electricity/verify", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["pan_match"] is True
    assert data["application"]["appl_stat"] == "APPROVED"
    assert data["application"]["dues_flag"] is True
