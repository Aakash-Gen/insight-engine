"""Critic agent — evaluates research quality and identifies gaps."""

from __future__ import annotations

import json
import structlog
import re
from datetime import datetime, timezone

from core.llm import chat
from agents.state import AgentLog, CritiqueResult, ResearchState
from core.config import settings

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a rigorous research quality critic. Evaluate the collected
research and identify gaps. Respond with valid JSON only — no markdown fences, no prose."""

_USER_TEMPLATE = """
Research topic: {topic}
Main question: {main_question}

Sub-questions to cover:
{sub_questions}

Search results summary ({num_results} results):
{results_summary}

Evaluate the research quality and respond with this exact JSON:
{{
  "has_gaps": <true|false>,
  "gaps": [<list of specific gap descriptions>],
  "additional_queries": [<3-5 targeted search queries to fill gaps>],
  "quality_score": <float 0.0-1.0>,
  "critique_summary": "<2-3 sentence summary of research quality>"
}}

Consider:
1. Are all sub-questions adequately addressed?
2. Is there a mix of recent and authoritative sources?
3. Are there conflicting perspectives that should be explored?
4. Are there obvious important angles not yet covered?
"""


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a LLM response."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


def _make_log(status: str, message: str) -> AgentLog:
    return AgentLog(
        agent="critic",
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _build_results_summary(search_results: list) -> str:
    """Produce a concise textual summary of search results for the critic prompt."""
    lines = []
    for i, r in enumerate(search_results[:20], 1):
        snippet = (r.get("content") or "")[:300].replace("\n", " ")
        lines.append(f"[{i}] {r.get('title', 'Untitled')} ({r.get('url', '')})\n    {snippet}")
    return "\n".join(lines)


def run_critic(state: ResearchState) -> dict:
    """
    Critic node: evaluates accumulated search results and decides if more research is needed.

    Forces ``has_gaps=False`` when iteration >= MAX_RESEARCH_ITERATIONS so the loop
    terminates even if the critic would otherwise request more searches.

    Returns a partial state dict consumed by LangGraph.
    """
    log_start = _make_log("running", "Evaluating research quality and coverage.")

    plan = state.get("plan")
    iteration = state.get("iteration", 0)
    search_results = state.get("search_results", [])

    # Depth-aware iteration cap: quick=1, standard=2, deep=3
    depth = state.get("depth", "standard")
    depth_max = {"quick": 1, "standard": 2, "deep": 3}
    max_iterations = depth_max.get(depth, settings.MAX_RESEARCH_ITERATIONS)

    if iteration >= max_iterations:
        critique = CritiqueResult(
            has_gaps=False,
            gaps=[],
            additional_queries=[],
            quality_score=0.75,
            critique_summary=f"Maximum iterations ({max_iterations}) for depth='{depth}' reached. Proceeding to synthesis.",
        )
        log_done = _make_log("done", f"Max iterations ({max_iterations}) reached; forcing synthesis.")
        logger.info("critic_force_complete", research_id=state["research_id"], iteration=iteration, depth=depth)
        return {"critique": critique, "logs": [log_start, log_done]}

    main_question = plan["main_question"] if plan else state["topic"]
    sub_questions_text = "\n".join(
        f"  - {q}" for q in (plan.get("sub_questions", []) if plan else [])
    )
    results_summary = _build_results_summary(search_results)

    prompt = _USER_TEMPLATE.format(
        topic=state["topic"],
        main_question=main_question,
        sub_questions=sub_questions_text or "  - (none specified)",
        num_results=len(search_results),
        results_summary=results_summary or "No results yet.",
    )

    try:
        raw, tokens_used = chat(system=_SYSTEM_PROMPT, user=prompt, max_tokens=1024)

        data = json.loads(_strip_fences(raw))
        critique = CritiqueResult(
            has_gaps=bool(data.get("has_gaps", False)),
            gaps=data.get("gaps", []),
            additional_queries=data.get("additional_queries", []),
            quality_score=float(data.get("quality_score", 0.5)),
            critique_summary=data.get("critique_summary", ""),
        )

        if critique["has_gaps"] and not critique["additional_queries"]:
            critique = CritiqueResult(**{**critique, "has_gaps": False})

        log_done = _make_log(
            "done",
            f"Quality score: {critique['quality_score']:.2f}. "
            f"Gaps found: {critique['has_gaps']}. {critique['critique_summary']}",
        )
        logger.info("Critic done for research_id=%s has_gaps=%s", state["research_id"], critique["has_gaps"])

        return {
            "critique": critique,
            "logs": [log_start, log_done],
            "token_usage": state.get("token_usage", 0) + tokens_used,
        }

    except json.JSONDecodeError as exc:
        logger.exception("Critic JSON parse error: %s", exc)
        critique = CritiqueResult(
            has_gaps=False, gaps=[], additional_queries=[],
            quality_score=0.5,
            critique_summary=f"Critique parse error; proceeding to synthesis. Error: {exc}",
        )
        log_done = _make_log("error", f"Critic parse error; defaulting to no-gaps. Error: {exc}")
        return {"critique": critique, "logs": [log_start, log_done]}

    except Exception as exc:
        logger.exception("Critic agent error: %s", exc)
        critique = CritiqueResult(
            has_gaps=False, gaps=[], additional_queries=[],
            quality_score=0.5, critique_summary=f"Critic failed: {exc}",
        )
        log_done = _make_log("error", f"Critic failed: {exc}")
        return {"critique": critique, "logs": [log_start, log_done]}
