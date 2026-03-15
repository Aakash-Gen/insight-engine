"""Self-RAG retriever — embeds raw search results and returns only relevant chunks."""

from __future__ import annotations

import logging
from typing import List

from rag.embeddings import embed_query, embed_texts

logger = logging.getLogger(__name__)

# Minimum cosine similarity score for a chunk to be returned (Self-RAG threshold)
RELEVANCE_THRESHOLD = 0.5


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_and_rerank(
    query: str,
    search_results: List[dict],
    top_k: int = 5,
) -> List[dict]:
    """
    Self-RAG style retrieval: embed raw search result contents, score each against
    the query embedding, and return only chunks that exceed the relevance threshold.

    This allows agents to retrieve semantically relevant context from the
    accumulated search results without a persistent vector store lookup.

    Args:
        query: The question or topic to match against.
        search_results: List of SearchResult dicts from the researcher agent.
        top_k: Maximum number of chunks to return.

    Returns:
        List of dicts with keys: content, url, title, score — filtered to
        similarity > RELEVANCE_THRESHOLD, sorted by score descending.
        Returns empty list on error or if no results pass the threshold.
    """
    if not search_results or not query:
        return []

    try:
        query_embedding = embed_query(query)
        if not query_embedding:
            logger.warning("retrieve_and_rerank: empty query embedding for query='%s'", query[:80])
            return []

        # Build content list for batch embedding
        contents = [r.get("content", "") for r in search_results]
        embeddings = embed_texts(contents)

        if not embeddings or len(embeddings) != len(search_results):
            logger.warning("retrieve_and_rerank: embedding count mismatch")
            return []

        # Score and filter
        scored = []
        for result, embedding in zip(search_results, embeddings):
            score = _cosine_similarity(query_embedding, embedding)
            if score >= RELEVANCE_THRESHOLD:
                scored.append({
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "score": score,
                })

        # Sort by relevance and cap
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored[:top_k]

        logger.info(
            "retrieve_and_rerank: %d/%d chunks passed threshold=%.2f for query='%s'",
            len(top_results), len(search_results), RELEVANCE_THRESHOLD, query[:80],
        )
        return top_results

    except Exception as exc:
        logger.exception("retrieve_and_rerank failed: %s", exc)
        return []
