"""
Tests for core/auth.py — JWT verification dependency.

Covers:
- Valid token accepted
- Missing Authorization header → 401
- Expired token → 401
- Tampered/invalid token → 401
- Token signed with wrong secret → 401
- Valid token via query param (SSE path)
- Missing query param token → 401
"""
from __future__ import annotations

import time
from unittest.mock import patch

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.auth import get_current_user, get_current_user_query
from core.config import settings
from tests.conftest import TOKEN_A, USER_A_ID, _mint_token, auth_header

# ---------------------------------------------------------------------------
# Minimal test app that exposes both auth dependencies
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/protected")
def protected_route(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"]}


@_test_app.get("/sse-protected")
def sse_route(user: dict = Depends(get_current_user_query)):
    return {"user_id": user["user_id"]}


@pytest.fixture()
def auth_client():
    return TestClient(_test_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Bearer header auth
# ---------------------------------------------------------------------------

class TestBearerAuth:
    def test_valid_token_accepted(self, auth_client):
        resp = auth_client.get("/protected", headers=auth_header(TOKEN_A))
        assert resp.status_code == 200
        assert resp.json()["user_id"] == USER_A_ID

    def test_missing_header_returns_401(self, auth_client):
        resp = auth_client.get("/protected")
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, auth_client):
        expired = jwt.encode(
            {"sub": USER_A_ID, "aud": "authenticated", "iat": 0, "exp": 1},
            settings.SUPABASE_JWT_SECRET,
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers=auth_header(expired))
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_wrong_secret_returns_401(self, auth_client):
        bad_token = jwt.encode(
            {"sub": USER_A_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers=auth_header(bad_token))
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, auth_client):
        resp = auth_client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_bearer_prefix_required(self, auth_client):
        # Raw token without "Bearer " prefix → 403 from HTTPBearer (auto_error=False returns None)
        resp = auth_client.get("/protected", headers={"Authorization": TOKEN_A})
        assert resp.status_code == 401

    def test_token_missing_sub_claim_returns_401(self, auth_client):
        no_sub = jwt.encode(
            {"email": "x@x.com", "aud": "authenticated", "exp": int(time.time()) + 3600},
            settings.SUPABASE_JWT_SECRET,
            algorithm="HS256",
        )
        resp = auth_client.get("/protected", headers=auth_header(no_sub))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Query param auth (SSE path)
# ---------------------------------------------------------------------------

class TestQueryParamAuth:
    def test_valid_token_in_query_param(self, auth_client):
        resp = auth_client.get(f"/sse-protected?token={TOKEN_A}")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == USER_A_ID

    def test_missing_token_param_returns_401(self, auth_client):
        resp = auth_client.get("/sse-protected")
        assert resp.status_code == 401

    def test_expired_token_in_query_param_returns_401(self, auth_client):
        expired = jwt.encode(
            {"sub": USER_A_ID, "aud": "authenticated", "iat": 0, "exp": 1},
            settings.SUPABASE_JWT_SECRET,
            algorithm="HS256",
        )
        resp = auth_client.get(f"/sse-protected?token={expired}")
        assert resp.status_code == 401
