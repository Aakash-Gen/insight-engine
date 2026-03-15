"""
In-process event bus for zero-lag SSE streaming.

Instead of polling Supabase every 1.5s, the background research task pushes
log events directly into a per-session asyncio.Queue. The SSE endpoint awaits
on the queue, delivering events instantly (sub-millisecond vs 1.5s lag).

Thread-safety: background tasks run in FastAPI's thread pool (sync functions).
Pushing from a sync thread to an asyncio.Queue requires loop.call_soon_threadsafe().
The running event loop is captured in the route handler (async context) and passed
to the background task.

Fallback: if the server restarts while a job is running (uvicorn --reload), the
queue is lost. The SSE endpoint falls back to Supabase polling for those sessions.
"""

from __future__ import annotations

import asyncio
from typing import Optional

# Sentinel object that signals the SSE generator to close the connection
DONE = object()

# Global registry: research_id → asyncio.Queue
_queues: dict[str, asyncio.Queue] = {}

# Loop registry: research_id → event loop (set when queue is created, used by agents for streaming)
_loops: dict[str, asyncio.AbstractEventLoop] = {}


def create(research_id: str, loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Queue:
    """Create and register a new event queue for a research session."""
    q: asyncio.Queue = asyncio.Queue(maxsize=5000)
    _queues[research_id] = q
    if loop is not None:
        _loops[research_id] = loop
    return q


def get(research_id: str) -> Optional[asyncio.Queue]:
    """Return the queue for a session, or None if not found (e.g. server restart)."""
    return _queues.get(research_id)


def remove(research_id: str) -> None:
    """Deregister the queue and loop after the session is finished."""
    _queues.pop(research_id, None)
    _loops.pop(research_id, None)


def _get_loop(research_id: str) -> Optional[asyncio.AbstractEventLoop]:
    """Return the event loop for a session, or None if not registered."""
    return _loops.get(research_id)


def push_log(research_id: str, log: dict, loop: asyncio.AbstractEventLoop) -> None:
    """
    Thread-safe: push a log dict from a sync background thread into the queue.
    Silently drops the event if the queue is full or not registered.
    """
    q = _queues.get(research_id)
    if q is not None:
        try:
            loop.call_soon_threadsafe(q.put_nowait, log)
        except asyncio.QueueFull:
            pass  # Client too slow to consume; drop rather than block


def push_done(research_id: str, status: str, loop: asyncio.AbstractEventLoop) -> None:
    """Thread-safe: signal stream completion."""
    q = _queues.get(research_id)
    if q is not None:
        try:
            loop.call_soon_threadsafe(q.put_nowait, {"__done__": True, "status": status})
        except asyncio.QueueFull:
            pass


def push_token(research_id: str, agent: str, token: str, loop: asyncio.AbstractEventLoop) -> None:
    """
    Thread-safe: push a single LLM output token from a sync background thread.

    Used by agents that support streaming (e.g. synthesizer) to deliver partial
    text to the SSE client as it is generated, rather than waiting for the full
    response.  Silently drops if the queue is full or the session is not registered.
    """
    q = _queues.get(research_id)
    if q is not None:
        try:
            loop.call_soon_threadsafe(q.put_nowait, {"__token__": True, "agent": agent, "text": token})
        except asyncio.QueueFull:
            pass
