"""Planner agent — decomposes a research topic into a structured ResearchPlan."""

from __future__ import annotations

import json
import structlog
import re
from datetime import datetime, timezone

from core.llm import chat
from agents.state import AgentLog, ResearchPlan, ResearchState

logger = structlog.get_logger(__name__)

_DEPTH_QUESTIONS: dict[str, int] = {
    "quick": 3,
    "standard": 5,
    "deep": 7,
}

_SYSTEM_PROMPT = """You are a research planning expert. Your job is to decompose a
research topic into a structured plan. You MUST respond with valid JSON only — no
markdown fences, no prose, just the raw JSON object."""

_USER_TEMPLATE = """
Research topic: {topic}
Depth: {depth} (generate {num_questions} sub-questions)
{override_section}

Respond with this exact JSON structure:
{{
  "main_question": "<one-sentence core research question>",
  "sub_questions": [<{num_questions} specific sub-questions as strings>],
  "search_keywords": [<8-12 targeted search keyword phrases as strings>]
}}
"""


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from an LLM response."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


def _make_log(status: str, message: str) -> AgentLog:
    return AgentLog(
        agent="planner",
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def run_planner(state: ResearchState) -> dict:
    """
    Planner node: calls the configured LLM to produce a ResearchPlan from the topic.

    Respects ``state['user_override']`` if provided, injecting that guidance
    into the prompt so the user can redirect the research direction.

    Returns a partial state dict consumed by LangGraph.
    """
    topic = state["topic"]
    depth = state.get("depth", "standard")
    override = state.get("user_override")
    num_questions = _DEPTH_QUESTIONS.get(depth, 5)

    override_section = (
        f"User guidance: {override}\nIncorporate the above guidance when forming the plan."
        if override
        else ""
    )

    prompt = _USER_TEMPLATE.format(
        topic=topic,
        depth=depth,
        num_questions=num_questions,
        override_section=override_section,
    )

    try:
        raw, tokens_used = chat(system=_SYSTEM_PROMPT, user=prompt, max_tokens=1024)

        plan_dict = json.loads(_strip_fences(raw))
        plan = ResearchPlan(
            main_question=plan_dict["main_question"],
            sub_questions=plan_dict["sub_questions"][:num_questions],
            search_keywords=plan_dict["search_keywords"],
        )

        log = _make_log("done", f"Research plan created with {len(plan['sub_questions'])} sub-questions.")
        logger.info("Planner completed for research_id=%s", state["research_id"])

        return {
            "plan": plan,
            "logs": [log],
            "token_usage": state.get("token_usage", 0) + tokens_used,
        }

    except json.JSONDecodeError as exc:
        logger.exception("Planner failed to parse LLM JSON response: %s", exc)
        fallback_plan = ResearchPlan(
            main_question=f"What are the key aspects of {topic}?",
            sub_questions=[f"What is {topic}?", f"Why does {topic} matter?", f"What are recent developments in {topic}?"],
            search_keywords=[topic, f"{topic} overview", f"{topic} research 2024"],
        )
        log = _make_log("error", f"Planner JSON parse error; using fallback plan. Error: {exc}")
        return {"plan": fallback_plan, "logs": [log]}

    except Exception as exc:
        logger.exception("Planner agent error: %s", exc)
        log = _make_log("error", f"Planner failed: {exc}")
        return {"logs": [log]}
