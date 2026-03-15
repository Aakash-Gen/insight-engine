"""LangGraph StateGraph definition for the ResearchMind multi-agent pipeline.

Flow:
  planner → researcher → critic ──(has_gaps AND iter < max)──→ researcher (loop)
                                └──(no gaps OR max reached)──→ synthesizer → writer → END
"""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from core.config import settings
from agents.state import ResearchState
from agents.planner import run_planner
from agents.researcher import run_researcher
from agents.critic import run_critic
from agents.synthesizer import run_synthesizer
from agents.writer import run_writer

logger = logging.getLogger(__name__)


def _should_continue_research(state: ResearchState) -> str:
    """
    Conditional routing function called after the critic node.

    Returns "researcher" if gaps remain and we haven't hit the iteration cap,
    otherwise returns "synthesizer" to proceed to report generation.
    """
    critique = state.get("critique")
    iteration = state.get("iteration", 0)

    if (
        critique is not None
        and critique.get("has_gaps", False)
        and iteration < settings.MAX_RESEARCH_ITERATIONS
    ):
        logger.info(
            "Critic: routing back to researcher (iteration=%d, max=%d)",
            iteration,
            settings.MAX_RESEARCH_ITERATIONS,
        )
        return "researcher"

    logger.info("Critic: routing to synthesizer (iteration=%d)", iteration)
    return "synthesizer"


def build_graph() -> StateGraph:
    """Construct and compile the ResearchMind LangGraph StateGraph."""
    graph = StateGraph(ResearchState)

    # Register nodes
    graph.add_node("planner", run_planner)
    graph.add_node("researcher", run_researcher)
    graph.add_node("critic", run_critic)
    graph.add_node("synthesizer", run_synthesizer)
    graph.add_node("writer", run_writer)

    # Linear edges
    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "critic")
    graph.add_edge("synthesizer", "writer")
    graph.add_edge("writer", END)

    # Conditional edge from critic
    graph.add_conditional_edges(
        "critic",
        _should_continue_research,
        {
            "researcher": "researcher",
            "synthesizer": "synthesizer",
        },
    )

    return graph.compile()


# Compiled singleton — imported by the API routes
research_graph = build_graph()
