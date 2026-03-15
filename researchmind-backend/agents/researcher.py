"""Researcher agent — executes web searches via Tavily and accumulates results."""

from __future__ import annotations

import structlog
from collections import defaultdict
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse

from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from agents.state import AgentLog, ResearchState, SearchResult

logger = structlog.get_logger(__name__)

_tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)


def _make_log(status: str, message: str) -> AgentLog:
    return AgentLog(
        agent="researcher",
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _tavily_search_with_retry(query: str) -> dict:
    """Call Tavily with automatic retries on transient errors."""
    return _tavily.search(
        query=query,
        search_depth="advanced",
        include_raw_content=True,
        max_results=settings.MAX_SEARCH_RESULTS,
    )


def _search(query: str, seen_urls: set[str]) -> tuple[List[SearchResult], List[dict]]:
    """
    Perform a single Tavily search and return deduplicated results and sources.

    Args:
        query: The search query string.
        seen_urls: Set of URLs already collected; mutated in-place.

    Returns:
        Tuple of (search_results, sources) where URLs not in seen_urls are added.
    """
    try:
        response = _tavily_search_with_retry(query)
        results: List[SearchResult] = []
        sources: List[dict] = []

        for r in response.get("results", []):
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            content = r.get("raw_content") or r.get("content") or ""
            results.append(
                SearchResult(
                    url=url,
                    title=r.get("title", ""),
                    content=content[:4000],  # cap per-result token use
                    score=r.get("score", 0.0),
                    query=query,
                )
            )
            sources.append({"url": url, "title": r.get("title", ""), "query": query})

        return results, sources

    except Exception as exc:
        logger.error("tavily_search_failed", query=query, error=str(exc))
        return [], []


def run_researcher(state: ResearchState) -> dict:
    """
    Researcher node: runs Tavily searches and appends results to state.

    On first iteration (iteration == 0) uses the plan's keywords + sub-questions.
    On subsequent iterations uses the critic's additional_queries.
    Deduplicates URLs across all iterations using existing sources.

    Returns a partial state dict consumed by LangGraph.
    """
    iteration = state.get("iteration", 0)
    plan = state.get("plan")
    critique = state.get("critique")

    # Build the set of already-seen URLs to avoid duplicates
    seen_urls: set[str] = {s["url"] for s in state.get("sources", []) if "url" in s}

    log_start = _make_log(
        "running" if iteration == 0 else "retrying",
        f"Starting search iteration {iteration + 1}.",
    )

    # Determine queries for this iteration
    if iteration == 0 or critique is None:
        queries: List[str] = []
        if plan:
            queries.extend(plan.get("search_keywords", [])[:4])
            queries.extend(plan.get("sub_questions", [])[:3])
        else:
            queries = [state["topic"]]
    else:
        queries = critique.get("additional_queries", [state["topic"]])

    raw_results: List[SearchResult] = []
    raw_sources: List[dict] = []

    for query in queries:
        results, sources = _search(query, seen_urls)
        raw_results.extend(results)
        raw_sources.extend(sources)

    # Domain diversity: cap at 2 results per domain so no single site dominates
    domain_counts: dict[str, int] = defaultdict(int)
    all_results: List[SearchResult] = []
    all_sources: List[dict] = []
    sorted_raw = sorted(raw_results, key=lambda r: r.get("score", 0), reverse=True)
    for result in sorted_raw:
        try:
            domain = urlparse(result.get("url", "")).netloc.replace("www.", "")
        except Exception:
            domain = result.get("url", "unknown")
        if domain_counts[domain] < 2:
            all_results.append(result)
            all_sources.append({"url": result.get("url", ""), "title": result.get("title", ""), "query": result.get("query", "")})
            domain_counts[domain] += 1

    log_done = _make_log(
        "done",
        f"Collected {len(all_results)} diverse results from {len(queries)} queries across {len(domain_counts)} domains (iteration {iteration + 1}).",
    )

    logger.info(
        "Researcher iteration %d: %d results for research_id=%s",
        iteration,
        len(all_results),
        state["research_id"],
    )

    return {
        "search_results": all_results,
        "sources": all_sources,
        "iteration": iteration + 1,
        "logs": [log_start, log_done],
    }
