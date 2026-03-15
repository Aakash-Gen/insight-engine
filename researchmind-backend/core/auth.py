"""JWT authentication dependency for FastAPI routes."""

from __future__ import annotations

import structlog
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    """
    Verify a Supabase JWT by calling Supabase's own /auth/v1/user endpoint
    via the admin client. This works regardless of JWT algorithm (HS256/RS256)
    and does not require the JWT secret to be configured locally.
    """
    from core.supabase_client import supabase
    try:
        resp = supabase.auth.get_user(token)
    except Exception as exc:
        logger.warning("jwt_verification_failed", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token.")

    if resp is None or resp.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return {
        "sub": resp.user.id,
        "email": resp.user.email or "",
    }


def _extract_user(payload: dict) -> dict:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user ID.")
    return {"user_id": user_id, "email": payload.get("email", "")}


def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> dict:
    """
    Dependency: validates Bearer JWT from Authorization header.
    Returns {"user_id": str, "email": str}.
    Raises HTTP 401 if missing or invalid.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required.")
    return _extract_user(_decode_token(credentials.credentials))


def get_current_user_query(
    token: Annotated[Optional[str], Query()] = None,
) -> dict:
    """
    Dependency for SSE endpoints: browsers cannot send custom headers via
    EventSource, so the JWT is passed as ?token=<jwt> query parameter.
    Returns {"user_id": str, "email": str}.
    Raises HTTP 401 if missing or invalid.
    """
    if not token:
        raise HTTPException(status_code=401, detail="token query parameter required.")
    return _extract_user(_decode_token(token))
