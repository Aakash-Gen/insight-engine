"""Unified LLM client — wraps Anthropic, xAI, and Groq behind a single interface.

Usage in agents:
    from core.llm import chat

    text, tokens = chat(
        system="You are a research expert.",
        user="Analyse this topic...",
        max_tokens=1024,
    )
"""

from __future__ import annotations

import structlog
from typing import Callable, Optional, Tuple

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings

logger = structlog.get_logger(__name__)

# Retry on any transient error: 3 attempts, 2→4→8s backoff
_llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)


def stream_chat(
    system: str,
    user: str,
    max_tokens: int = 2048,
    on_token: Optional[Callable[[str], None]] = None,
) -> Tuple[str, int]:
    """
    Like ``chat()`` but calls ``on_token(chunk)`` for each text chunk as it
    arrives from the LLM.  Falls back to regular ``chat()`` if ``on_token``
    is None.

    Streaming providers:
    - Anthropic: ``client.messages.stream()`` context manager
    - xAI / Groq: OpenAI-compatible streaming (``stream=True``)

    Token count for OpenAI-compat streaming is estimated from text length
    (1 token ≈ 4 chars) because usage metadata is not available in all
    streaming responses.
    """
    if on_token is None:
        return chat(system, user, max_tokens)

    if settings.LLM_PROVIDER == "xai":
        return _stream_xai(system, user, max_tokens, on_token)
    if settings.LLM_PROVIDER == "groq":
        return _stream_groq(system, user, max_tokens, on_token)
    return _stream_anthropic(system, user, max_tokens, on_token)


def _stream_anthropic(system: str, user: str, max_tokens: int, on_token: Callable[[str], None]) -> Tuple[str, int]:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    full_text = ""
    with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
            on_token(chunk)
        msg = stream.get_final_message()
        tokens = msg.usage.input_tokens + msg.usage.output_tokens
    logger.debug("stream_llm_call", provider="anthropic", model=settings.CLAUDE_MODEL, tokens=tokens)
    return full_text, tokens


def _stream_xai(system: str, user: str, max_tokens: int, on_token: Callable[[str], None]) -> Tuple[str, int]:
    if not settings.XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY is not set.")
    from openai import OpenAI
    client = OpenAI(api_key=settings.XAI_API_KEY, base_url="https://api.x.ai/v1")
    full_text = ""
    for chunk in client.chat.completions.create(
        model=settings.GROK_MODEL, max_tokens=max_tokens, stream=True,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    ):
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_text += delta
            on_token(delta)
    tokens = max(1, len(full_text) // 4)
    logger.debug("stream_llm_call", provider="xai", model=settings.GROK_MODEL, tokens=tokens)
    return full_text, tokens


def _stream_groq(system: str, user: str, max_tokens: int, on_token: Callable[[str], None]) -> Tuple[str, int]:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")
    from openai import OpenAI
    client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    full_text = ""
    for chunk in client.chat.completions.create(
        model=settings.GROQ_MODEL, max_tokens=max_tokens, stream=True,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    ):
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_text += delta
            on_token(delta)
    tokens = max(1, len(full_text) // 4)
    logger.debug("stream_llm_call", provider="groq", model=settings.GROQ_MODEL, tokens=tokens)
    return full_text, tokens


def chat(
    system: str,
    user: str,
    max_tokens: int = 2048,
) -> Tuple[str, int]:
    """
    Send a system + user message to the configured LLM and return the response.

    Dispatches to Anthropic, xAI, or Groq based on ``settings.LLM_PROVIDER``.
    Each provider path has automatic retry (3 attempts, exponential backoff).

    Args:
        system: System prompt string.
        user: User message string.
        max_tokens: Maximum tokens in the completion.

    Returns:
        Tuple of (response_text, total_tokens_used).
    """
    if settings.LLM_PROVIDER == "xai":
        return _chat_xai(system, user, max_tokens)
    if settings.LLM_PROVIDER == "groq":
        return _chat_groq(system, user, max_tokens)
    return _chat_anthropic(system, user, max_tokens)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

@_llm_retry
def _chat_anthropic(system: str, user: str, max_tokens: int) -> Tuple[str, int]:
    """Call Anthropic Claude and return (text, tokens)."""
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    from anthropic import Anthropic  # lazy import

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    logger.debug("llm_call", provider="anthropic", model=settings.CLAUDE_MODEL, tokens=tokens)
    return text, tokens


# ---------------------------------------------------------------------------
# xAI (Grok) — OpenAI-compatible API
# ---------------------------------------------------------------------------

@_llm_retry
def _chat_xai(system: str, user: str, max_tokens: int) -> Tuple[str, int]:
    """Call xAI Grok via the OpenAI-compatible endpoint and return (text, tokens)."""
    if not settings.XAI_API_KEY:
        raise RuntimeError("XAI_API_KEY is not set.")

    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=settings.XAI_API_KEY, base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(
        model=settings.GROK_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    tokens = response.usage.prompt_tokens + response.usage.completion_tokens
    logger.debug("llm_call", provider="xai", model=settings.GROK_MODEL, tokens=tokens)
    return text, tokens


# ---------------------------------------------------------------------------
# Groq — OpenAI-compatible API (fast inference, free tier)
# ---------------------------------------------------------------------------

@_llm_retry
def _chat_groq(system: str, user: str, max_tokens: int) -> Tuple[str, int]:
    """Call Groq via the OpenAI-compatible endpoint and return (text, tokens)."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")

    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    tokens = response.usage.prompt_tokens + response.usage.completion_tokens
    logger.debug("llm_call", provider="groq", model=settings.GROQ_MODEL, tokens=tokens)
    return text, tokens
