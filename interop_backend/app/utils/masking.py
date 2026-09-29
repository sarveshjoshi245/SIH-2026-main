def mask_pan(pan: str | None) -> str:
    """Mask a 10-character PAN string for safe audit logging and privacy.
    
    Example:
        'ABCDE1234F' -> 'AB****34F'
    """
    if not pan:
        return "UNKNOWN"
    clean_pan = pan.strip()
    if len(clean_pan) < 5:
        return "****"
    prefix = clean_pan[:2]
    suffix = clean_pan[-3:]
    return f"{prefix}****{suffix}"


def mask_token(token: str | None) -> str:
    """Mask a token or API key for safe logging."""
    if not token or len(token) < 8:
        return "******"
    return f"{token[:4]}...{token[-4:]}"
