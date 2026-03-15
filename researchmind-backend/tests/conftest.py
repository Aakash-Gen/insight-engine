"""
Shared fixtures for the ResearchMind test suite.

Strategy
--------
- We use FastAPI's TestClient (synchronous) via httpx.
- All Supabase calls are monkey-patched so tests never touch the real DB.
- JWT tokens are minted with the real SUPABASE_JWT_SECRET from settings so
  the auth dependency works identically to production.
- LLM and Tavily calls are patched at the function level.
"""
from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from core.config import settings

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

USER_A_ID = str(uuid.uuid4())
USER_B_ID = str(uuid.uuid4())
RESEARCH_ID = str(uuid.uuid4())

# Consistent secret used for all test token minting and verification.
# Falls back to a fixed string when SUPABASE_JWT_SECRET is unset in CI.
TEST_JWT_SECRET: str = settings.SUPABASE_JWT_SECRET or "researchmind-ci-test-secret"


def _mint_token(user_id: str, email: str = "test@example.com") -> str:
    """Mint a valid Supabase-style HS256 JWT for tests."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


TOKEN_A = _mint_token(USER_A_ID, "usera@example.com")
TOKEN_B = _mint_token(USER_B_ID, "userb@example.com")
EXPIRED_TOKEN = jwt.encode(
    {"sub": USER_A_ID, "aud": "authenticated", "iat": 0, "exp": 1},  # exp in the past
    TEST_JWT_SECRET,
    algorithm="HS256",
)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Supabase mock builder
# ---------------------------------------------------------------------------

def _supabase_row(overrides: dict | None = None) -> dict:
    """Return a minimal research_sessions row."""
    base = {
        "id": RESEARCH_ID,
        "user_id": USER_A_ID,
        "topic": "Test topic",
        "depth": "standard",
        "status": "complete",
        "is_complete": True,
        "logs": [],
        "sources": [],
        "overall_confidence": 0.85,
        "token_usage": 100,
        "deleted_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "final_report": {
            "title": "Test Report",
            "executive_summary": "Summary.",
            "key_findings": ["Finding 1"],
            "sections": [],
            "conflicting_perspectives": "",
            "conclusion": "Conclusion.",
            "overall_confidence": 0.85,
            "quality_breakdown": {
                "source_diversity": 0.8,
                "recency": 0.9,
                "depth": 0.7,
                "cross_validation": 0.85,
            },
        },
    }
    if overrides:
        base.update(overrides)
    return base


def make_supabase_mock(row: dict | None = None, rows: list | None = None):
    """
    Build a mock that satisfies the chained Supabase query builder pattern:
        supabase.table(...).select(...).eq(...).single().execute()
    """
    data = row if row is not None else (rows if rows is not None else [])
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    chain.execute.return_value = result
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.single.return_value = chain
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.delete.return_value = chain
    chain.order.return_value = chain

    mock_sb = MagicMock()
    mock_sb.table.return_value = chain
    return mock_sb, chain, result


# ---------------------------------------------------------------------------
# Autouse fixture — mock Supabase auth.get_user for all tests
# ---------------------------------------------------------------------------

def _fake_get_user(token: str):
    """
    Decode a test JWT locally instead of hitting the real Supabase API.

    - Valid token  → returns mock response with user.id / user.email set
    - Expired token → returns response with user=None (triggers "Invalid or expired token." detail)
    - Wrong secret / malformed → re-raises so _decode_token catches it and returns 401
    """
    import jwt as _jwt

    try:
        payload = _jwt.decode(
            token,
            TEST_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except _jwt.ExpiredSignatureError:
        resp = MagicMock()
        resp.user = None
        return resp
    except Exception:
        raise  # _decode_token will catch and return HTTP 401

    mock_user = MagicMock()
    mock_user.id = payload.get("sub")
    mock_user.email = payload.get("email", "")
    resp = MagicMock()
    resp.user = mock_user
    return resp


@pytest.fixture(autouse=True)
def mock_supabase_auth():
    """Prevent any test from hitting the real Supabase Auth API."""
    with patch("core.supabase_client.supabase") as mock_sb:
        mock_sb.auth.get_user.side_effect = _fake_get_user
        yield mock_sb


# ---------------------------------------------------------------------------
# App fixture — patch Supabase at module level before importing the app
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    Return a TestClient with the real app.
    Supabase is patched; the agent graph background task is also patched
    so /research/start never actually runs the pipeline.
    """
    with (
        patch("api.routes.research.supabase") as mock_research_sb,
        patch("api.routes.reports.supabase") as mock_reports_sb,
        patch("api.routes.research._run_research_graph"),  # don't run the real graph
    ):
        # Default: every Supabase query returns USER_A's session row
        row = _supabase_row()
        for mock_sb in (mock_research_sb, mock_reports_sb):
            _, chain, result = make_supabase_mock(row=row)
            result.data = row
            mock_sb.table.return_value = chain

        from main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture()
def supabase_row():
    return _supabase_row
