import uuid


def generate_transaction_id(prefix: str = "ELEC-TXN") -> str:
    """Generate a readable uppercase transaction ID."""
    token = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{token}"


def generate_status_transaction_id() -> str:
    """Generate status transaction ID."""
    return generate_transaction_id(prefix="ELEC-STATUS")


def generate_verify_transaction_id() -> str:
    """Generate verify transaction ID."""
    return generate_transaction_id(prefix="ELEC-VERIFY")
