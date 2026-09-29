import pytest
from app.config import settings
from app.utils.masking import mask_pan


def test_pan_masking_utility():
    assert mask_pan("ABCDE1234F") == "AB****34F"
    assert mask_pan("FGHIJ5678K") == "FG****78K"
    assert mask_pan(None) == "UNKNOWN"
    assert mask_pan("") == "UNKNOWN"


def test_chaos_simulation_returns_503(client, interop_headers, monkeypatch):
    # Enable chaos and set 100% failure rate for test verification
    monkeypatch.setattr(settings, "CHAOS_ENABLED", True)
    monkeypatch.setattr(settings, "VERIFY_FAILURE_RATE", 1.0)
    monkeypatch.setattr(settings, "SIMULATED_DELAY_RATE", 0.0)

    payload = {
        "application_number": "ELEC-2026-00101",
        "pan": "ABCDE1234F"
    }
    response = client.post("/api/electricity/verify", json=payload, headers=interop_headers)
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "DEPARTMENT_UNAVAILABLE"
    assert data["department"] == "ELECTRICITY_DISTRIBUTION"
    assert data["retryable"] is True
    assert data["transaction_id"].startswith("ELEC-")
