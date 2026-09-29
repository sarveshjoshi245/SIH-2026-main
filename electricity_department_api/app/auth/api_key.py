import json
import fnmatch
from typing import Optional, List
from fastapi import Header, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.electricity import ApiConsumer
from app.utils.transaction import generate_transaction_id


def get_api_consumer(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> ApiConsumer:
    """Validate X-API-Key header against registered ApiConsumers in SQLite DB.
    
    Raises 401 if missing, invalid, or inactive.
    """
    transaction_id = generate_transaction_id()
    request.state.transaction_id = transaction_id

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "UNAUTHORIZED",
                "message": "Missing or invalid API key",
                "transaction_id": transaction_id
            }
        )

    consumer = db.query(ApiConsumer).filter(
        ApiConsumer.api_key == x_api_key,
        ApiConsumer.is_active == True
    ).first()

    if not consumer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "UNAUTHORIZED",
                "message": "Missing or invalid API key",
                "transaction_id": transaction_id
            }
        )

    request.state.consumer_id = consumer.consumer_id
    return consumer


def require_scope(required_pattern: str):
    """Dependency factory checking if consumer has permission for endpoint pattern."""
    def scope_checker(
        request: Request,
        consumer: ApiConsumer = Depends(get_api_consumer)
    ) -> ApiConsumer:
        try:
            allowed_scopes: List[str] = json.loads(consumer.allowed_scopes)
        except Exception:
            allowed_scopes = [s.strip() for s in consumer.allowed_scopes.split(",") if s.strip()]

        # Check if any allowed scope matches the required pattern or request path
        has_permission = False
        for scope in allowed_scopes:
            if scope == "*":
                has_permission = True
                break
            if fnmatch.fnmatch(request.url.path, scope) or fnmatch.fnmatch(required_pattern, scope):
                has_permission = True
                break

        if not has_permission:
            transaction_id = getattr(request.state, "transaction_id", generate_transaction_id())
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "FORBIDDEN",
                    "message": "Consumer is not authorized for this endpoint",
                    "transaction_id": transaction_id
                }
            )
        return consumer

    return scope_checker
