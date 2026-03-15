"""Pydantic request/response schemas for the ResearchMind API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class StartResearchRequest(BaseModel):
    """Body for POST /research/start."""

    topic: str = Field(..., min_length=3, max_length=500, description="Research topic or question.")
    depth: str = Field(default="standard", description="Research depth: 'quick', 'standard', or 'deep'.")
    # user_id is extracted from the JWT — not accepted from the request body.

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        """Ensure depth is one of the accepted values."""
        allowed = {"quick", "standard", "deep"}
        if v not in allowed:
            raise ValueError(f"depth must be one of {allowed}")
        return v


class ResearchResponse(BaseModel):
    """Response for POST /research/start."""

    research_id: str
    status: str
    message: str


class OverrideRequest(BaseModel):
    """Body for POST /research/{research_id}/override."""

    message: str = Field(..., min_length=1, max_length=1000)


class OverrideResponse(BaseModel):
    """Response for POST /research/{research_id}/override."""

    status: str


class QualityBreakdown(BaseModel):
    """Confidence sub-scores for the final report."""

    source_diversity: float
    recency: float
    depth: float
    cross_validation: float


class ReportSectionOut(BaseModel):
    """A single section in the report response."""

    title: str
    content: str
    sources: List[str] = []


class ReportResponse(BaseModel):
    """Response for GET /reports/{research_id}."""

    research_id: str
    title: str
    executive_summary: str = ""
    key_findings: List[str] = []
    sections: List[ReportSectionOut] = []
    conflicting_perspectives: str = ""
    conclusion: str = ""
    sources: List[dict] = []
    overall_confidence: float = 0.0
    quality_breakdown: Optional[QualityBreakdown] = None
    created_at: Optional[datetime] = None


class ReportListItem(BaseModel):
    """Summary row for GET /reports/user/{user_id}."""

    research_id: str
    title: str
    overall_confidence: float
    depth: str
    created_at: Optional[datetime] = None


class AgentLogEvent(BaseModel):
    """SSE event payload streamed to the client."""

    research_id: str
    agent: str
    status: str
    message: str
    timestamp: str


class CompletionEvent(BaseModel):
    """SSE terminal event sent when research finishes."""

    type: str = "complete"
    research_id: str
