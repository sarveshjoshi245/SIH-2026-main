import random
import time
from typing import Optional

# In-memory OTP store. In production replace with Redis + TTL.
# Structure: { "AADHAAR:123456789012": {"otp": "452901", "expires_at": 1725350000.0} }
_otp_store: dict[str, dict] = {}
_OTP_TTL_SECONDS = 300  # 5 minutes


def _make_key(identifier: str, method: str) -> str:
    """e.g. 'AADHAAR:123456789012' or 'PAN:ABCDE1234F'"""
    return f"{method.upper()}:{identifier.upper().strip()}"


def generate_otp(identifier: str, method: str) -> str:
    """Generate and store a 6-digit OTP for the given Aadhaar or PAN."""
    otp = str(random.randint(100000, 999999))
    key = _make_key(identifier, method)
    _otp_store[key] = {
        "otp": otp,
        "expires_at": time.time() + _OTP_TTL_SECONDS,
    }
    return otp


def verify_otp(identifier: str, method: str, otp_provided: str) -> bool:
    """Verify OTP. Returns True if valid and not expired, clears it on success."""
    key = _make_key(identifier, method)
    record = _otp_store.get(key)
    if not record:
        return False
    if time.time() > record["expires_at"]:
        del _otp_store[key]
        return False
    if record["otp"] != otp_provided.strip():
        return False
    # Consume OTP
    del _otp_store[key]
    return True


def peek_otp(identifier: str, method: str) -> Optional[str]:
    """Debug helper: view the stored OTP without consuming it (for demo/testing)."""
    key = _make_key(identifier, method)
    record = _otp_store.get(key)
    if record and time.time() <= record["expires_at"]:
        return record["otp"]
    return None
