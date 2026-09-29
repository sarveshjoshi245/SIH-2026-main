def test_missing_api_key_returns_401(client):
    response = client.get("/api/electricity/applications/ELEC-2026-00101")
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "UNAUTHORIZED"
    assert "Missing or invalid API key" in data["message"]


def test_invalid_api_key_returns_401(client):
    response = client.get(
        "/api/electricity/applications/ELEC-2026-00101",
        headers={"X-API-Key": "non_existent_key_9999"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "UNAUTHORIZED"


def test_insufficient_scope_returns_403(client, clearance_headers):
    # clearance key has scope ["/api/electricity/*"] but NOT ["/api/audit"] or ["/api/admin/*"]
    response = client.get(
        "/api/audit",
        headers=clearance_headers
    )
    assert response.status_code == 403
    data = response.json()
    assert data["status"] == "FORBIDDEN"
    assert "not authorized" in data["message"]
