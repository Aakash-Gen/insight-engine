"""
Tests for GET /reports/{id}, GET /reports/user/{user_id}, DELETE /reports/{id}.

Covers:
- get_report: public access, 404, 202 (in-progress), 200 with full report
- list_user_reports: auth required, user can only list own reports (403 for others)
- delete_report: auth required, only owner can delete, 404 on missing/deleted
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.conftest import (
    RESEARCH_ID,
    TOKEN_A,
    TOKEN_B,
    USER_A_ID,
    USER_B_ID,
    auth_header,
    _supabase_row,
    make_supabase_mock,
)


# ---------------------------------------------------------------------------
# GET /reports/{research_id}  — public, no auth required
# ---------------------------------------------------------------------------

class TestGetReport:
    def test_complete_report_returned_without_auth(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["research_id"] == RESEARCH_ID
        assert body["title"] == "Test Report"
        assert body["overall_confidence"] == 0.85

    def test_quality_breakdown_present(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}")
        assert resp.status_code == 200
        qb = resp.json()["quality_breakdown"]
        assert qb is not None
        assert "source_diversity" in qb

    def test_missing_report_returns_404(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            _, chain, result = make_supabase_mock(row=None)
            result.data = None
            mock_sb.table.return_value = chain

            resp = client.get(f"/reports/does-not-exist")
        assert resp.status_code == 404

    def test_in_progress_returns_202(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            row = _supabase_row({"is_complete": False, "status": "running"})
            _, chain, result = make_supabase_mock(row=row)
            result.data = row
            mock_sb.table.return_value = chain

            resp = client.get(f"/reports/{RESEARCH_ID}")
        assert resp.status_code == 202

    def test_key_findings_list_returned(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}")
        assert isinstance(resp.json()["key_findings"], list)

    def test_sources_list_returned(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}")
        assert isinstance(resp.json()["sources"], list)


# ---------------------------------------------------------------------------
# GET /reports/user/{user_id}
# ---------------------------------------------------------------------------

class TestListUserReports:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get(f"/reports/user/{USER_A_ID}")
        assert resp.status_code == 401

    def test_owner_can_list_own_reports(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            rows = [_supabase_row()]
            _, chain, result = make_supabase_mock(rows=rows)
            result.data = rows
            mock_sb.table.return_value = chain

            resp = client.get(
                f"/reports/user/{USER_A_ID}",
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["research_id"] == RESEARCH_ID
        assert items[0]["title"] == "Test Report"

    def test_cannot_list_other_users_reports(self, client):
        """USER_B cannot fetch USER_A's report list."""
        resp = client.get(
            f"/reports/user/{USER_A_ID}",
            headers=auth_header(TOKEN_B),
        )
        assert resp.status_code == 403

    def test_empty_list_returned_when_no_reports(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            _, chain, result = make_supabase_mock(rows=[])
            result.data = []
            mock_sb.table.return_value = chain

            resp = client.get(
                f"/reports/user/{USER_A_ID}",
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_report_list_item_fields(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            rows = [_supabase_row()]
            _, chain, result = make_supabase_mock(rows=rows)
            result.data = rows
            mock_sb.table.return_value = chain

            resp = client.get(
                f"/reports/user/{USER_A_ID}",
                headers=auth_header(TOKEN_A),
            )
        item = resp.json()[0]
        assert set(item.keys()) >= {"research_id", "title", "overall_confidence", "depth"}


# ---------------------------------------------------------------------------
# DELETE /reports/{research_id}
# ---------------------------------------------------------------------------

class TestDeleteReport:
    def test_unauthenticated_returns_401(self, client):
        resp = client.delete(f"/reports/{RESEARCH_ID}")
        assert resp.status_code == 401

    def test_owner_can_delete(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            row = _supabase_row()
            _, chain, result = make_supabase_mock(row=row)
            result.data = row
            mock_sb.table.return_value = chain

            resp = client.delete(
                f"/reports/{RESEARCH_ID}",
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_non_owner_gets_403(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            row = _supabase_row({"user_id": USER_A_ID})
            _, chain, result = make_supabase_mock(row=row)
            result.data = row
            mock_sb.table.return_value = chain

            resp = client.delete(
                f"/reports/{RESEARCH_ID}",
                headers=auth_header(TOKEN_B),
            )
        assert resp.status_code == 403

    def test_missing_report_returns_404(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            _, chain, result = make_supabase_mock(row=None)
            result.data = None
            mock_sb.table.return_value = chain

            resp = client.delete(
                f"/reports/nonexistent",
                headers=auth_header(TOKEN_A),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /reports/{research_id}/export
# ---------------------------------------------------------------------------

class TestExportReport:
    def test_export_md_returns_text(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}/export?format=md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        body = resp.text
        assert "Test Report" in body

    def test_export_txt_returns_text_plain(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}/export?format=txt")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    def test_export_invalid_format_returns_400(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}/export?format=pdf")
        assert resp.status_code == 400

    def test_export_contains_content_disposition(self, client):
        resp = client.get(f"/reports/{RESEARCH_ID}/export?format=md")
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_export_missing_report_returns_404(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            _, chain, result = make_supabase_mock(row=None)
            result.data = None
            mock_sb.table.return_value = chain

            resp = client.get(f"/reports/nonexistent/export?format=md")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /reports/{research_id}/ask
# ---------------------------------------------------------------------------

class TestAskReport:
    def test_ask_returns_answer(self, client):
        with patch("api.routes.reports.chat", return_value=("The answer.", 10)):
            resp = client.post(
                f"/reports/{RESEARCH_ID}/ask",
                json={"question": "What are the key findings?"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "The answer."
        assert body["research_id"] == RESEARCH_ID

    def test_ask_empty_question_returns_400(self, client):
        resp = client.post(
            f"/reports/{RESEARCH_ID}/ask",
            json={"question": "   "},
        )
        assert resp.status_code == 400

    def test_ask_missing_report_returns_404(self, client):
        with patch("api.routes.reports.supabase") as mock_sb:
            _, chain, result = make_supabase_mock(row=None)
            result.data = None
            mock_sb.table.return_value = chain

            resp = client.post(
                f"/reports/nonexistent/ask",
                json={"question": "What is this about?"},
            )
        assert resp.status_code == 404

    def test_ask_llm_error_returns_500(self, client):
        with patch("api.routes.reports.chat", side_effect=Exception("LLM down")):
            resp = client.post(
                f"/reports/{RESEARCH_ID}/ask",
                json={"question": "Tell me more."},
            )
        assert resp.status_code == 500
