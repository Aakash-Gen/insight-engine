"""Supabase pgvector store for research content chunks."""

from __future__ import annotations

import logging
import uuid
from typing import List

from core.supabase_client import supabase
from rag.embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)

TABLE_NAME = "research_chunks"


def upsert_chunks(research_id: str, chunks: List[dict]) -> None:
    """
    Embed chunk content and upsert into the Supabase research_chunks table.

    Each dict in ``chunks`` must have a ``content`` key. Optional keys:
    ``metadata`` (dict). Any existing rows with the same research_id and
    matching content are replaced via Supabase's upsert.

    Args:
        research_id: UUID string for the parent research session.
        chunks: List of dicts with at least ``{"content": "..."}`` keys.
    """
    if not chunks:
        return

    texts = [c.get("content", "") for c in chunks]
    embeddings = embed_texts(texts)

    if not embeddings:
        logger.warning("upsert_chunks: embedding returned empty for research_id=%s", research_id)
        return

    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        rows.append({
            "id": str(uuid.uuid4()),
            "research_id": research_id,
            "content": chunk.get("content", ""),
            "embedding": embedding,
            "metadata": chunk.get("metadata", {}),
        })

    try:
        supabase.table(TABLE_NAME).upsert(rows).execute()
        logger.info("Upserted %d chunks for research_id=%s", len(rows), research_id)
    except Exception as exc:
        logger.exception("upsert_chunks failed for research_id=%s: %s", research_id, exc)


def similarity_search(query: str, research_id: str, top_k: int = 5) -> List[dict]:
    """
    Find the most semantically similar chunks for a given query within a research session.

    Uses Supabase RPC ``match_research_chunks`` which performs cosine similarity
    via pgvector. Requires the function to be defined in Supabase (see supabase_client.py).

    Args:
        query: Natural language query to match against.
        research_id: UUID string scoping the search to one session.
        top_k: Maximum number of results to return.

    Returns:
        List of dicts with keys: id, content, metadata, similarity.
        Returns empty list on error.
    """
    query_embedding = embed_query(query)
    if not query_embedding:
        logger.warning("similarity_search: empty query embedding for research_id=%s", research_id)
        return []

    try:
        response = supabase.rpc(
            "match_research_chunks",
            {
                "query_embedding": query_embedding,
                "match_research_id": research_id,
                "match_count": top_k,
            },
        ).execute()
        return response.data or []
    except Exception as exc:
        logger.exception("similarity_search failed for research_id=%s: %s", research_id, exc)
        return []
