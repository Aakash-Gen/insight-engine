"""LangGraph state definitions for the ResearchMind multi-agent pipeline."""

from __future__ import annotations

from typing import Annotated, List, Optional
from typing_extensions import TypedDict


def _add(existing: list, new: list) -> list:
    """Reducer that appends new items to an existing list (used by Annotated)."""
    return existing + new


# ---------------------------------------------------------------------------
# Sub-type definitions
# ---------------------------------------------------------------------------

class ResearchPlan(TypedDict):
    """Output of the Planner agent."""
    main_question: str
    sub_questions: List[str]
    search_keywords: List[str]


class SearchResult(TypedDict):
    """A single web search result returned by the Researcher agent."""
    url: str
    title: str
    content: str
    score: float
    query: str


class CritiqueResult(TypedDict):
    """Quality evaluation produced by the Critic agent."""
    has_gaps: bool
    gaps: List[str]
    additional_queries: List[str]
    quality_score: float      # 0.0 – 1.0
    critique_summary: str


class ReportSection(TypedDict):
    """A single section of the final structured report."""
    title: str
    content: str
    sources: List[str]


class AgentLog(TypedDict):
    """Progress log entry appended by every agent node."""
    agent: str
    status: str      # "running" | "done" | "retrying" | "error"
    message: str
    timestamp: str


# ---------------------------------------------------------------------------
# Primary state
# ---------------------------------------------------------------------------

class ResearchState(TypedDict):
    """
    Central state object threaded through every node in the LangGraph graph.

    Fields annotated with ``Annotated[List[X], _add]`` accumulate across nodes
    (LangGraph calls the reducer when merging partial states).
    """
    topic: str
    depth: str                                          # "quick" | "standard" | "deep"
    research_id: str
    user_override: Optional[str]

    # Planner output
    plan: Optional[ResearchPlan]

    # Researcher output — accumulates across iterations
    search_results: Annotated[List[SearchResult], _add]

    # Loop counter
    iteration: int

    # Critic output
    critique: Optional[CritiqueResult]

    # Synthesizer output
    synthesized_findings: Optional[str]

    # Writer output
    report_sections: Optional[List[ReportSection]]
    final_report: Optional[str]

    # Sources accumulate across iterations
    sources: Annotated[List[dict], _add]

    # Scalar metrics
    overall_confidence: Optional[float]

    # Progress logs accumulate across all agents
    logs: Annotated[List[AgentLog], _add]

    # Token tracking
    token_usage: int

    # Terminal flag
    is_complete: bool
