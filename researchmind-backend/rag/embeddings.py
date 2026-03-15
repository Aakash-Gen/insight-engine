"""Embedding utilities using sentence-transformers (all-MiniLM-L6-v2)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """
    Lazily load and cache the sentence-transformer model.

    The model is downloaded on first call and cached in memory for the
    lifetime of the process.
    """
    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of text strings into dense vectors.

    Args:
        texts: List of strings to embed.

    Returns:
        List of float vectors, one per input string.
        Returns empty list on error.
    """
    if not texts:
        return []
    try:
        model = _get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()
    except Exception as exc:
        logger.exception("embed_texts failed: %s", exc)
        return []


def embed_query(query: str) -> List[float]:
    """
    Embed a single query string.

    Args:
        query: The search query to embed.

    Returns:
        Float vector of dimension 384, or empty list on error.
    """
    result = embed_texts([query])
    return result[0] if result else []
