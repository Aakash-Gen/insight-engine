"""Reports API routes: fetch, list, delete, export, and Q&A."""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from api.schemas import QualityBreakdown, ReportListItem, ReportResponse, ReportSectionOut
from core.auth import get_current_user
from core.llm import chat
from core.supabase_client import supabase

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_final_report(row: dict) -> dict:
    """Extract and JSON-parse final_report from a DB row."""
    final_report = row.get("final_report") or {}
    if isinstance(final_report, str):
        try:
            final_report = json.loads(final_report)
        except json.JSONDecodeError:
            final_report = {}
    return final_report


def _parse_report(research_id: str, row: dict) -> ReportResponse:
    """Convert a raw Supabase research_sessions row into a ReportResponse."""
    final_report = _parse_final_report(row)

    sections: List[ReportSectionOut] = []
    for s in final_report.get("sections", []):
        sections.append(ReportSectionOut(
            title=s.get("title", ""),
            content=s.get("content", ""),
            sources=s.get("sources", []),
        ))

    qb_data = final_report.get("quality_breakdown", {})
    quality_breakdown = None
    if qb_data:
        try:
            quality_breakdown = QualityBreakdown(
                source_diversity=float(qb_data.get("source_diversity", 0.0)),
                recency=float(qb_data.get("recency", 0.0)),
                depth=float(qb_data.get("depth", 0.0)),
                cross_validation=float(qb_data.get("cross_validation", 0.0)),
            )
        except Exception:
            pass

    created_at = None
    raw_ts = row.get("created_at")
    if raw_ts:
        try:
            created_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except Exception:
            pass

    return ReportResponse(
        research_id=research_id,
        title=final_report.get("title", row.get("topic", "Untitled Research")),
        executive_summary=final_report.get("executive_summary", ""),
        key_findings=final_report.get("key_findings", []),
        sections=sections,
        conflicting_perspectives=final_report.get("conflicting_perspectives", ""),
        conclusion=final_report.get("conclusion", ""),
        sources=row.get("sources") or [],
        overall_confidence=float(row.get("overall_confidence") or final_report.get("overall_confidence") or 0.0),
        quality_breakdown=quality_breakdown,
        created_at=created_at,
    )


def _fetch_complete_row(research_id: str) -> dict:
    """Fetch a completed, non-deleted research_sessions row or raise HTTP errors."""
    try:
        row = (
            supabase.table("research_sessions")
            .select("*")
            .eq("id", research_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
    except Exception as exc:
        logger.exception("db_fetch_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Database error.")

    if not row.data:
        raise HTTPException(status_code=404, detail="Report not found.")

    if not row.data.get("is_complete"):
        raise HTTPException(status_code=202, detail="Research is still in progress.")

    return row.data


def _report_to_markdown(row: dict) -> str:
    """Render a research_sessions row as a Markdown document."""
    fr = _parse_final_report(row)
    lines: List[str] = []

    title = fr.get("title") or row.get("topic") or "Untitled Research"
    lines.append(f"# {title}\n")

    created_raw = row.get("created_at", "")
    if created_raw:
        try:
            dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            lines.append(f"*Generated: {dt.strftime('%B %d, %Y')}*\n")
        except Exception:
            pass

    confidence = float(row.get("overall_confidence") or fr.get("overall_confidence") or 0.0)
    lines.append(f"*Confidence score: {confidence:.0%}*\n")

    exec_summary = fr.get("executive_summary", "")
    if exec_summary:
        lines.append("## Executive Summary\n")
        lines.append(f"{exec_summary}\n")

    key_findings = fr.get("key_findings", [])
    if key_findings:
        lines.append("## Key Findings\n")
        for finding in key_findings:
            lines.append(f"- {finding}")
        lines.append("")

    for section in fr.get("sections", []):
        lines.append(f"## {section.get('title', 'Section')}\n")
        lines.append(f"{section.get('content', '')}\n")
        section_sources = section.get("sources", [])
        if section_sources:
            lines.append("**Sources:**")
            for src in section_sources:
                lines.append(f"- {src}")
            lines.append("")

    conflicts = fr.get("conflicting_perspectives", "")
    if conflicts and conflicts != "No significant conflicts identified.":
        lines.append("## Conflicting Perspectives\n")
        lines.append(f"{conflicts}\n")

    conclusion = fr.get("conclusion", "")
    if conclusion:
        lines.append("## Conclusion\n")
        lines.append(f"{conclusion}\n")

    all_sources = row.get("sources") or []
    if all_sources:
        lines.append("## Sources\n")
        for i, src in enumerate(all_sources, 1):
            url = src.get("url", "")
            src_title = src.get("title") or url
            lines.append(f"{i}. [{src_title}]({url})")

    return "\n".join(lines)


def _build_report_context(fr: dict) -> str:
    """Flatten a final_report dict into a text context for Q&A."""
    parts: List[str] = []

    exec_summary = fr.get("executive_summary", "")
    if exec_summary:
        parts.append(f"Executive Summary:\n{exec_summary}")

    key_findings = fr.get("key_findings", [])
    if key_findings:
        parts.append("Key Findings:\n" + "\n".join(f"- {f}" for f in key_findings))

    for section in fr.get("sections", []):
        parts.append(f"Section — {section.get('title', '')}:\n{section.get('content', '')}")

    conflicts = fr.get("conflicting_perspectives", "")
    if conflicts:
        parts.append(f"Conflicting Perspectives:\n{conflicts}")

    conclusion = fr.get("conclusion", "")
    if conclusion:
        parts.append(f"Conclusion:\n{conclusion}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Schemas specific to this module
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    research_id: str


# ---------------------------------------------------------------------------
# GET /reports/user/{user_id}   — must be before /{research_id} to avoid
# FastAPI matching "user" as a research_id path param
# ---------------------------------------------------------------------------

@router.get("/user/{user_id}", response_model=List[ReportListItem])
async def list_user_reports(
    user_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> List[ReportListItem]:
    """
    List all completed research reports for a given user, newest first.

    Requires auth. The JWT user_id must match the path parameter — users
    cannot list other users' reports.
    """
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        rows = (
            supabase.table("research_sessions")
            .select("id, topic, depth, overall_confidence, final_report, created_at")
            .eq("user_id", user_id)
            .eq("is_complete", True)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.exception("list_user_reports_error", user_id=user_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Database error.")

    items: List[ReportListItem] = []
    for row in rows.data or []:
        final_report = _parse_final_report(row)
        title = final_report.get("title") or row.get("topic") or "Untitled Research"

        created_at = None
        raw_ts = row.get("created_at")
        if raw_ts:
            try:
                created_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except Exception:
                pass

        items.append(ReportListItem(
            research_id=row["id"],
            title=title,
            overall_confidence=float(row.get("overall_confidence") or 0.0),
            depth=row.get("depth", "standard"),
            created_at=created_at,
        ))

    return items


# ---------------------------------------------------------------------------
# GET /reports/{research_id}
# ---------------------------------------------------------------------------

@router.get("/{research_id}", response_model=ReportResponse)
async def get_report(research_id: str) -> ReportResponse:
    """
    Retrieve a completed research report by its UUID.

    No auth required — report UUIDs are unguessable and this endpoint
    enables future public sharing via direct link.
    """
    data = _fetch_complete_row(research_id)
    return _parse_report(research_id, data)


# ---------------------------------------------------------------------------
# DELETE /reports/{research_id}
# ---------------------------------------------------------------------------

@router.delete("/{research_id}")
async def delete_report(
    research_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Soft-delete a research report. Requires auth; only the owner may delete.
    """
    try:
        row = (
            supabase.table("research_sessions")
            .select("id, user_id")
            .eq("id", research_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
        )
    except Exception as exc:
        logger.exception("delete_report_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Database error.")

    if not row.data:
        raise HTTPException(status_code=404, detail="Report not found or already deleted.")

    if row.data.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        supabase.table("research_sessions").update({
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", research_id).execute()
    except Exception as exc:
        logger.exception("delete_report_update_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Database error.")

    logger.info("report_soft_deleted", research_id=research_id, user_id=current_user["user_id"])
    return {"status": "deleted", "research_id": research_id}


# ---------------------------------------------------------------------------
# GET /reports/{research_id}/export
# ---------------------------------------------------------------------------

@router.get("/{research_id}/export", response_class=PlainTextResponse)
async def export_report(
    research_id: str,
    format: str = Query(default="md", description="Export format: 'md' (Markdown) or 'txt'."),
) -> PlainTextResponse:
    """
    Export a completed research report as plain Markdown or text.

    No auth required (same public-sharing rationale as GET /reports/{id}).
    The Content-Disposition header prompts the browser to download the file.
    """
    if format not in ("md", "txt"):
        raise HTTPException(status_code=400, detail="format must be 'md' or 'txt'.")

    data = _fetch_complete_row(research_id)
    content = _report_to_markdown(data)

    safe_title = (data.get("topic") or research_id)[:60].replace(" ", "_")
    filename = f"{safe_title}.{format}"

    return PlainTextResponse(
        content=content,
        media_type="text/markdown" if format == "md" else "text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /reports/{research_id}/ask
# ---------------------------------------------------------------------------

_QA_SYSTEM = (
    "You are a helpful research assistant. Answer the user's question using ONLY "
    "the provided research report context. Be concise, accurate, and cite specific "
    "sections when relevant. If the answer is not in the report, say so clearly."
)


@router.post("/{research_id}/ask", response_model=AskResponse)
async def ask_report(
    research_id: str,
    body: AskRequest,
) -> AskResponse:
    """
    Ask a follow-up question about a completed research report.

    Retrieves the full report from the database and uses the configured LLM
    to answer the question grounded in the report content.

    No auth required (same UUID-as-capability model as GET /reports/{id}).
    """
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty.")

    data = _fetch_complete_row(research_id)
    fr = _parse_final_report(data)
    context = _build_report_context(fr)

    if not context.strip():
        raise HTTPException(status_code=422, detail="Report has no content to query.")

    user_prompt = (
        f"Research Report Context:\n\n{context}\n\n"
        f"---\n\nQuestion: {body.question.strip()}"
    )

    try:
        answer, _ = chat(system=_QA_SYSTEM, user=user_prompt, max_tokens=1024)
        logger.info("report_qa_answered", research_id=research_id)
        return AskResponse(answer=answer.strip(), research_id=research_id)
    except Exception as exc:
        logger.exception("report_qa_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate answer.")
