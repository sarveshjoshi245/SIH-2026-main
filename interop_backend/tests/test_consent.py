def test_grant_consent(client, abc_headers):
    payload = {
        "purpose": "New Plant Environmental Clearances",
        "allowed_departments": ["LAND", "ELECTRICITY", "POLLUTION"],
        "expires_in_days": 180
    }
    response = client.post("/api/consent", json=payload, headers=abc_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["organization_pan"] == "ABCDE1234F"
    assert data["is_active"] is True


def test_get_my_consents(client, abc_headers):
    response = client.get("/api/consent/my", headers=abc_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["organization_pan"] == "ABCDE1234F"
