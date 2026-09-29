def test_status_endpoint_returns_pending_and_retryable(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    response = client.get("/api/electricity/status/ELEC-2026-00102", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["application_number"] == "ELEC-2026-00102"
    assert data["application_status"] == "PENDING"
    assert data["inspection_status"] == "PENDING"
    assert data["meter_status"] == "NOT_INSTALLED"
    assert data["connection_status"] == "NOT_CONNECTED"
    assert data["retryable"] is True
    assert data["transaction_id"].startswith("ELEC-STATUS-")


def test_status_endpoint_terminal_state_retryable_false(client, interop_headers):
    headers = {**interop_headers, "X-Bypass-Chaos": "true"}
    response = client.get("/api/electricity/status/ELEC-2026-00101", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["application_status"] == "APPROVED"
    assert data["connection_status"] == "ENERGIZED"
    assert data["retryable"] is False
