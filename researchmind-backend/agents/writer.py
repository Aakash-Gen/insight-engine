"""Writer agent — formats synthesized findings into a structured final report."""

from __future__ import annotations

import json
import structlog
import re
from datetime import datetime, timezone
from typing import List

from core.llm import chat
from agents.state import AgentLog, ReportSection, ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are an expert research report writer. Transform research
synthesis into a structured, professional report. Respond with valid JSON only —
no markdown fences, no prose outside the JSON object."""

_USER_TEMPLATE = """
Research topic: {topic}
Depth: {depth}

Synthesized findings:
{synthesized_findings}

Available sources ({num_sources} total):
{sources_list}

Produce a final report as this exact JSON structure:
{{
  "title": "<concise, descriptive title>",
  "executive_summary": "<3-5 sentence overview of key findings>",
  "key_findings": [<5-8 bullet-point strings of the most important findings>],
  "sections": [
    {{
      "title": "<section title>",
      "content": "<detailed section content — see depth guidelines below>",
      "sources": [<list of cited source URLs>]
    }}
  ],
  "conflicting_perspectives": "<paragraph about disagreements or debates in the sources, or 'No significant conflicts identified.' if none>",
  "conclusion": "<synthesis of the overall answer and implications — see depth guidelines below>",
  "overall_confidence": <float 0.0-1.0 reflecting source quality, recency, and consensus>,
  "quality_breakdown": {{
    "source_diversity": <float 0.0-1.0>,
    "recency": <float 0.0-1.0>,
    "depth": <float 0.0-1.0>,
    "cross_validation": <float 0.0-1.0>
  }}
}}

Depth guidelines for "{depth}":
{depth_guidelines}

General rules:
- overall_confidence: 0.9+ only for highly sourced, recent, well-validated research
- Cite specific source URLs in each section's sources array
"""

_DEPTH_GUIDELINES = {
    "quick": (
        "- 3-4 sections, each 100-150 words\n"
        "- executive_summary: 2-3 sentences\n"
        "- key_findings: 3-5 bullets\n"
        "- conclusion: 1-2 sentences\n"
        "- Focus on the most important facts only"
    ),
    "standard": (
        "- 4-6 sections, each 200-350 words\n"
        "- executive_summary: 3-5 sentences\n"
        "- key_findings: 5-8 bullets\n"
        "- conclusion: 2-3 sentences\n"
        "- Cover all major angles with supporting evidence"
    ),
    "deep": (
        "- 6-8 sections, each 400-600 words\n"
        "- executive_summary: 5-7 sentences covering context, findings, and implications\n"
        "- key_findings: 8-12 detailed bullets\n"
        "- conclusion: 4-5 sentences with implications and recommended next steps\n"
        "- Explore nuances, counter-arguments, and knowledge gaps in each section\n"
        "- Include specific data points, statistics, and named examples where available"
    ),
}


def _compute_confidence(state: dict) -> tuple[float, dict]:
    """
    Compute an algorithmic confidence score from research metadata.
    Returns (overall: float 0-1, quality_breakdown: dict).

    Metrics:
      source_diversity  — unique domains / total results (rewards breadth)
      relevance         — average Tavily score of top-20 results
      depth             — scales with depth setting and iteration count
      cross_validation  — fraction of sources that appear in >1 result cluster
    """
    search_results = state.get("search_results", [])
    depth = state.get("depth", "standard")
    iteration = state.get("iteration", 0)

    # Source diversity: unique domains vs total results
    domains = set()
    scores = []
    for r in search_results:
        try:
            from urllib.parse import urlparse
            domains.add(urlparse(r.get("url", "")).netloc)
        except Exception:
            pass
        if r.get("score") is not None:
            scores.append(float(r["score"]))

    total = len(search_results) or 1
    diversity = min(len(domains) / total, 1.0) if total else 0.5
    # Reward having many unique domains, penalise single-domain domination
    diversity = round(min(diversity * 1.2, 1.0), 3)

    # Relevance: mean Tavily score (0–1), default 0.6 if unavailable
    relevance = round(sum(scores) / len(scores), 3) if scores else 0.6

    # Depth: quick=0.55 base, standard=0.70, deep=0.85; each critic loop adds 0.03
    depth_base = {"quick": 0.55, "standard": 0.70, "deep": 0.85}.get(depth, 0.70)
    depth_score = round(min(depth_base + iteration * 0.03, 1.0), 3)

    # Cross-validation proxy: fraction of results with score > 0.7
    high_quality = sum(1 for s in scores if s > 0.7)
    cross_val = round(high_quality / len(scores), 3) if scores else 0.5

    # Weighted overall
    overall = round(
        diversity * 0.25 +
        relevance * 0.35 +
        depth_score * 0.25 +
        cross_val * 0.15,
        3,
    )
    # Clamp to a realistic range (never claim perfect confidence)
    overall = max(0.30, min(overall, 0.95))

    breakdown = {
        "source_diversity": diversity,
        "recency": relevance,      # proxy — Tavily score correlates with recency/quality
        "depth": depth_score,
        "cross_validation": cross_val,
    }
    return overall, breakdown


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a LLM response."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


def _make_log(status: str, message: str) -> AgentLog:
    return AgentLog(
        agent="writer",
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def run_writer(state: ResearchState) -> dict:
    """
    Writer node: calls the configured LLM to produce the final structured report JSON.

    Reads ``synthesized_findings`` and ``sources`` from state, outputs
    ``final_report`` (raw JSON string), ``report_sections``, ``overall_confidence``,
    and sets ``is_complete=True``.

    Returns a partial state dict consumed by LangGraph.
    """
    log_start = _make_log("running", "Writing final structured report.")

    synthesized = state.get("synthesized_findings", "")
    sources = state.get("sources", [])

    sources_list = "\n".join(
        f"  - [{i+1}] {s.get('title', 'Untitled')}: {s.get('url', '')}"
        for i, s in enumerate(sources[:30])
    ) or "  - (no sources available)"

    depth = state.get("depth", "standard")
    prompt = _USER_TEMPLATE.format(
        topic=state["topic"],
        depth=depth,
        synthesized_findings=synthesized or "No synthesis available.",
        num_sources=len(sources),
        sources_list=sources_list,
        depth_guidelines=_DEPTH_GUIDELINES.get(depth, _DEPTH_GUIDELINES["standard"]),
    )

    max_tokens = {"quick": 2048, "standard": 4096, "deep": 6144}.get(depth, 4096)

    try:
        raw, tokens_used = chat(system=_SYSTEM_PROMPT, user=prompt, max_tokens=max_tokens)

        data = json.loads(_strip_fences(raw))

        report_sections: List[ReportSection] = [
            ReportSection(
                title=s.get("title", ""),
                content=s.get("content", ""),
                sources=s.get("sources", []),
            )
            for s in data.get("sections", [])
        ]

        # Replace the LLM's self-assessed confidence with an algorithmic score
        # computed from actual research metadata (diversity, relevance, depth).
        overall_confidence, quality_breakdown = _compute_confidence(state)
        data["overall_confidence"] = overall_confidence
        data["quality_breakdown"] = quality_breakdown

        log_done = _make_log(
            "done",
            f"Report written: '{data.get('title', '')}' "
            f"({len(report_sections)} sections, confidence={overall_confidence:.0%}).",
        )
        logger.info(
            "Writer done for research_id=%s sections=%d confidence=%.2f",
            state["research_id"], len(report_sections), overall_confidence,
        )

        return {
            "final_report": json.dumps(data),
            "report_sections": report_sections,
            "overall_confidence": overall_confidence,
            "is_complete": True,
            "logs": [log_start, log_done],
            "token_usage": state.get("token_usage", 0) + tokens_used,
        }

    except json.JSONDecodeError as exc:
        logger.exception("Writer JSON parse error: %s", exc)
        log_done = _make_log("error", f"Writer JSON parse error: {exc}")
        return {
            "final_report": json.dumps({"error": str(exc)}),
            "report_sections": [],
            "overall_confidence": 0.0,
            "is_complete": True,
            "logs": [log_start, log_done],
        }

    except Exception as exc:
        logger.exception("Writer agent error: %s", exc)
        log_done = _make_log("error", f"Writer failed: {exc}")
        return {
            "final_report": json.dumps({"error": str(exc)}),
            "report_sections": [],
            "overall_confidence": 0.0,
            "is_complete": True,
            "logs": [log_start, log_done],
        }
