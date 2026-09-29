def test_user_registration(client):
    payload = {
        "email": "newuser@testcorp.com",
        "password": "Password123",
        "organization_name": "Test Corp Ltd",
        "organization_pan": "TESTP1234T",
        "aadhaar_number": "123456789099"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@testcorp.com"
    assert data["organization_pan"] == "TESTP1234T"
    assert data["aadhaar_masked"] == "XXXX-XXXX-9099"
    assert data["is_aadhaar_verified"] is True


def test_user_login_success(client):
    payload = {
        "email": "applicant@abcindustries.com",
        "password": "SecretPass123"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["organization_pan"] == "ABCDE1234F"


def test_user_login_wrong_password(client):
    payload = {
        "email": "applicant@abcindustries.com",
        "password": "WrongPassword999"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401


def test_otp_login_flow(client):
    # 1. Request OTP for Aadhaar
    req_res = client.post("/api/auth/otp/request", json={
        "login_method": "AADHAAR",
        "identifier": "111111111101"
    })
    assert req_res.status_code == 200
    otp = req_res.json()["demo_otp"]
    assert otp is not None

    # 2. Verify OTP
    ver_res = client.post("/api/auth/otp/verify", json={
        "login_method": "AADHAAR",
        "identifier": "111111111101",
        "otp": otp
    })
    assert ver_res.status_code == 200
    token_data = ver_res.json()
    assert "access_token" in token_data
    assert token_data["organization_pan"] == "ABCDE1234F"


def test_profile_endpoint(client, abc_headers):
    response = client.get("/api/auth/me", headers=abc_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "applicant@abcindustries.com"
    assert data["organization_pan"] == "ABCDE1234F"
