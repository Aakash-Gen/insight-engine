"""
Tests for POST /research/start and POST /research/{id}/override.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import (
    RESEARCH_ID,
    TOKEN_A,
    TOKEN_B,
    USER_A_ID,
    USER_B_ID,
    auth_header,
    _supabase_row,
)


def _configure_mock(mock_sb, row):
    """Configure a patch()-managed supabase mock to return the given row."""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=row)
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.single.return_value = chain
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.order.return_value = chain
    mock_sb.table.return_value = chain
    return chain


# ---------------------------------------------------------------------------
# POST /research/start
# ---------------------------------------------------------------------------

class TestStartResearch:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post("/research/start", json={"topic": "AI trends", "depth": "standard"})
        assert resp.status_code == 401

    def test_authenticated_returns_research_id(self, client):
        resp = client.post(
            "/research/start",
            json={"topic": "AI trends", "depth": "standard"},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "research_id" in body
        assert body["status"] == "started"

    def test_extra_fields_in_body_are_ignored(self, client):
        """user_id in the body is silently ignored; JWT is the source of truth."""
        resp = client.post(
            "/research/start",
            json={"topic": "AI trends", "depth": "standard", "user_id": "attacker-id"},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 200

    def test_invalid_depth_returns_422(self, client):
        resp = client.post(
            "/research/start",
            json={"topic": "AI trends", "depth": "ultra"},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 422

    def test_topic_too_short_returns_422(self, client):
        resp = client.post(
            "/research/start",
            json={"topic": "AI", "depth": "standard"},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 422

    def test_topic_too_long_returns_422(self, client):
        resp = client.post(
            "/research/start",
            json={"topic": "x" * 501, "depth": "standard"},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 422

    def test_all_depth_values_accepted(self, client):
        for depth in ("quick", "standard", "deep"):
            resp = client.post(
                "/research/start",
                json={"topic": "AI trends", "depth": depth},
                headers=auth_header(TOKEN_A),
            )
            assert resp.status_code == 200, f"depth={depth} should be accepted"

    def test_supabase_insert_uses_jwt_user_id(self, client):
        """The session must be persisted with the JWT user_id, not a body value."""
        with (
            patch("api.routes.research.supabase") as mock_sb,
            patch("api.routes.research._run_research_graph"),
        ):
            chain = _configure_mock(mock_sb, _supabase_row())

            client.post(
                "/research/start",
                json={"topic": "AI trends", "depth": "standard"},
                headers=auth_header(TOKEN_A),
            )

            call_args = chain.insert.call_args
            assert call_args is not None, "insert() was never called"
            inserted = call_args[0][0]
            assert inserted["user_id"] == USER_A_ID

    def test_rate_limiter_unit_raises_429_after_limit(self):
        """
        Unit-test the rate limiter closure directly.
        FastAPI resolves Depends() at route registration time, so we cannot
        patch the name after app creation. Instead we test the function itself.
        """
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from core.limiter import make_ip_rate_limiter

        limiter = make_ip_rate_limiter(calls=3, seconds=60)
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"

        # First 3 calls succeed
        for _ in range(3):
            limiter(mock_request)  # should not raise

        # 4th call exceeds the limit
        with pytest.raises(HTTPException) as exc_info:
            limiter(mock_request)
        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# POST /research/{id}/override
# ---------------------------------------------------------------------------

class TestOverrideResearch:
    def test_unauthenticated_returns_401(self, client):
        resp = client.post(
            f"/research/{RESEARCH_ID}/override",
            json={"message": "Focus on renewable energy"},
        )
        assert resp.status_code == 401

    def test_owner_can_override(self, client):
        with (
            patch("api.routes.research.supabase") as mock_sb,
            patch("api.routes.research._run_research_graph"),
        ):
            row = _supabase_row({"user_id": USER_A_ID, "status": "running", "is_complete": False})
            _configure_mock(mock_sb, row)

            resp = client.post(
                f"/research/{RESEARCH_ID}/override",
                json={"message": "Focus on renewable energy"},
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "override_received"

    def test_non_owner_gets_403(self, client):
        with (
            patch("api.routes.research.supabase") as mock_sb,
            patch("api.routes.research._run_research_graph"),
        ):
            # Session belongs to USER_A; USER_B tries to override
            row = _supabase_row({"user_id": USER_A_ID})
            _configure_mock(mock_sb, row)

            resp = client.post(
                f"/research/{RESEARCH_ID}/override",
                json={"message": "Hijack this"},
                headers=auth_header(TOKEN_B),
            )
        assert resp.status_code == 403

    def test_nonexistent_session_returns_404(self, client):
        with (
            patch("api.routes.research.supabase") as mock_sb,
            patch("api.routes.research._run_research_graph"),
        ):
            _configure_mock(mock_sb, None)

            resp = client.post(
                f"/research/nonexistent-id/override",
                json={"message": "test"},
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 404

    def test_empty_message_returns_422(self, client):
        resp = client.post(
            f"/research/{RESEARCH_ID}/override",
            json={"message": ""},
            headers=auth_header(TOKEN_A),
        )
        assert resp.status_code == 422
