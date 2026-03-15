"""Synthesizer agent — merges all search results into coherent findings."""

from __future__ import annotations

import structlog
from datetime import datetime, timezone

from core.llm import chat, stream_chat
from core.config import settings
from core import stream_bus
from agents.state import AgentLog, ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPTS = {
    "quick":    "You are an expert research synthesizer. Merge the search results into a concise summary. Use [SOURCE N] citations. Write approximately 400-600 words. Be direct and factual.",
    "standard": "You are an expert research synthesizer. Merge multiple web search results into clear, coherent findings. Use [SOURCE N] citations. Write approximately 800-1200 words. Be analytical, not merely descriptive.",
    "deep":     "You are an expert research synthesizer. Produce a comprehensive, deeply analytical synthesis of all search results. Use [SOURCE N] citations throughout. Write 1500-2500 words. Explore nuances, tensions, implications, and knowledge gaps in depth.",
}

_USER_TEMPLATE = """
Research topic: {topic}
Main question: {main_question}

Sub-questions to address:
{sub_questions}

Source materials:
{sources_text}

Instructions:
- Address EVERY sub-question explicitly
- Note consensus views and conflicting perspectives
- Cite sources inline as [SOURCE 1], [SOURCE 2], etc.
- Be analytical: identify patterns, implications, and knowledge gaps
- Do NOT use markdown headers — write flowing prose with clear paragraph breaks
"""


def _make_log(status: str, message: str) -> AgentLog:
    return AgentLog(
        agent="synthesizer",
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _build_sources_text(search_results: list, depth: str = "standard") -> str:
    """Format top search results as numbered source blocks for the synthesis prompt.

    Context limits are driven by both depth and provider:
      quick:    10 results × 500 chars
      standard: 15 results × 900 chars
      deep:     25 results × 1500 chars
    Groq free-tier TPM cap further reduces the per-result char limit.
    Results are sorted by score descending so the most relevant are kept.
    """
    depth_config = {
        "quick":    (10,  500),
        "standard": (15,  900),
        "deep":     (25, 1500),
    }
    max_results, max_chars = depth_config.get(depth, (15, 900))

    # Groq has a smaller context window — cap per-result chars to stay within TPM limits
    if settings.LLM_PROVIDER == "groq":
        max_results = min(max_results, 12)
        max_chars = min(max_chars, 600)

    sorted_results = sorted(search_results, key=lambda r: r.get("score", 0), reverse=True)
    blocks = []
    for i, r in enumerate(sorted_results[:max_results], 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = (r.get("content") or "")[:max_chars].strip()
        blocks.append(f"[SOURCE {i}] {title}\nURL: {url}\n{content}")
    return "\n\n".join(blocks)


def run_synthesizer(state: ResearchState) -> dict:
    """
    Synthesizer node: asks the configured LLM to merge all accumulated search
    results into a coherent narrative with inline citations. Output length scales
    with depth: quick≈500w, standard≈1000w, deep≈2000w.

    Returns a partial state dict consumed by LangGraph.
    """
    log_start = _make_log("running", "Synthesizing findings from all research sources.")

    depth = state.get("depth", "standard")
    plan = state.get("plan")
    search_results = state.get("search_results", [])

    main_question = plan["main_question"] if plan else state["topic"]
    sub_questions_text = "\n".join(
        f"  - {q}" for q in (plan.get("sub_questions", []) if plan else [])
    ) or "  - (answer the main question comprehensively)"

    sources_text = _build_sources_text(search_results, depth) or "No search results available."

    prompt = _USER_TEMPLATE.format(
        topic=state["topic"],
        main_question=main_question,
        sub_questions=sub_questions_text,
        sources_text=sources_text,
    )

    system_prompt = _SYSTEM_PROMPTS.get(depth, _SYSTEM_PROMPTS["standard"])
    max_tokens = {"quick": 1024, "standard": 2048, "deep": 4096}.get(depth, 2048)

    try:
        # Use streaming synthesis if the SSE bus has a queue for this session.
        # Tokens are pushed in real-time so the frontend shows synthesis as it generates.
        research_id = state["research_id"]
        loop = stream_bus._get_loop(research_id)
        if loop is not None:
            def _on_token(token: str) -> None:
                stream_bus.push_token(research_id, "synthesizer", token, loop)
            synthesized, tokens_used = stream_chat(system=system_prompt, user=prompt, max_tokens=max_tokens, on_token=_on_token)
        else:
            synthesized, tokens_used = chat(system=system_prompt, user=prompt, max_tokens=max_tokens)
        synthesized = synthesized.strip()

        word_count = len(synthesized.split())
        log_done = _make_log("done", f"Synthesis complete ({word_count} words, {len(search_results)} sources).")
        logger.info("Synthesizer done for research_id=%s words=%d", state["research_id"], word_count)

        return {
            "synthesized_findings": synthesized,
            "logs": [log_start, log_done],
            "token_usage": state.get("token_usage", 0) + tokens_used,
        }

    except Exception as exc:
        logger.exception("Synthesizer agent error: %s", exc)
        fallback = f"Synthesis could not be completed due to an error: {exc}. Raw results are available in sources."
        log_done = _make_log("error", f"Synthesizer failed: {exc}")
        return {"synthesized_findings": fallback, "logs": [log_start, log_done]}
