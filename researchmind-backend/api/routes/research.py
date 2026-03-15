"""Research API routes: start, stream, and override."""

from __future__ import annotations

import asyncio
import json
import signal
import structlog
import uuid
from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from agents.graph import research_graph
from agents.state import ResearchState
from api.schemas import (
    OverrideRequest,
    OverrideResponse,
    ResearchResponse,
    StartResearchRequest,
)
from core.auth import get_current_user, get_current_user_query
from core.config import settings
from core import stream_bus
from core.email import send_research_complete_email
from core.limiter import research_rate_limit
from core.supabase_client import supabase
from rag.vectorstore import upsert_chunks

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/research", tags=["research"])

# Fallback polling interval when the in-process queue is unavailable
# (e.g. server restarted while a job was running)
_FALLBACK_POLL_INTERVAL = 1.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_session(research_id: str) -> dict:
    """Fetch a research session row; raises 404 if not found."""
    try:
        row = (
            supabase.table("research_sessions")
            .select("id, user_id, is_complete, status, logs")
            .eq("id", research_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error("db_fetch_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Database error.")
    if not row.data:
        raise HTTPException(status_code=404, detail="Research session not found.")
    return row.data


def _assert_owner(session: dict, user_id: str) -> None:
    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")


# ---------------------------------------------------------------------------
# Background task: run the graph and persist results
# ---------------------------------------------------------------------------

def _run_research_graph(
    research_id: str,
    initial_state: ResearchState,
    loop: asyncio.AbstractEventLoop,
    user_email: str = "",
) -> None:
    """
    Execute the LangGraph research pipeline as a background task.

    Pushes log events to the in-process stream bus (zero-lag SSE) AND writes
    them to Supabase (persistence). Hard-times out after RESEARCH_TIMEOUT_SECONDS.
    """
    log = logger.bind(research_id=research_id)

    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Timed out after {settings.RESEARCH_TIMEOUT_SECONDS}s")

    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(settings.RESEARCH_TIMEOUT_SECONDS)
    except (AttributeError, OSError, ValueError):
        # SIGALRM is Unix-only and only works in the main thread;
        # gracefully skip the hard timeout when running in a background thread
        pass

    try:
        last_log_count = 0

        for event in research_graph.stream(initial_state, stream_mode="values"):
            current_logs = event.get("logs", [])
            new_logs = current_logs[last_log_count:]
            last_log_count = len(current_logs)

            if new_logs:
                # Push new logs to the in-process stream bus (instant delivery)
                for entry in new_logs:
                    stream_bus.push_log(research_id, entry, loop)

                # Also persist to Supabase for durability
                try:
                    supabase.table("research_sessions").update({
                        "logs": current_logs,
                    }).eq("id", research_id).execute()
                except Exception as exc:
                    logger.error("log_persist_error", research_id=research_id, error=str(exc))

        # Re-invoke to get terminal state (stream gives snapshots)
        final_state = research_graph.invoke(initial_state)

        # Embed and store search results in pgvector for Q&A
        search_results = final_state.get("search_results", [])
        if search_results:
            chunks = [
                {
                    "content": r.get("content", ""),
                    "metadata": {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "query": r.get("query", ""),
                    },
                }
                for r in search_results
                if r.get("content")
            ]
            upsert_chunks(research_id, chunks)

        final_report_raw = final_state.get("final_report")
        final_report_dict = None
        if final_report_raw:
            try:
                final_report_dict = json.loads(final_report_raw)
            except json.JSONDecodeError:
                final_report_dict = {"raw": final_report_raw}

        supabase.table("research_sessions").update({
            "status": "complete",
            "logs": final_state.get("logs", []),
            "final_report": final_report_dict,
            "sources": final_state.get("sources", []),
            "overall_confidence": final_state.get("overall_confidence"),
            "is_complete": True,
            "token_usage": final_state.get("token_usage", 0),
        }).eq("id", research_id).execute()

        stream_bus.push_done(research_id, "complete", loop)
        log.info("pipeline_complete")

        # Email notification — no-op when RESEND_API_KEY / SMTP_HOST not configured
        if user_email:
            send_research_complete_email(
                to_email=user_email,
                topic=initial_state["topic"],
                research_id=research_id,
            )

    except TimeoutError as exc:
        log.error("pipeline_timeout", error=str(exc))
        stream_bus.push_done(research_id, "failed", loop)
        _mark_failed(research_id, f"Research timed out after {settings.RESEARCH_TIMEOUT_SECONDS}s")

    except Exception as exc:
        log.exception("pipeline_failed", error=str(exc))
        stream_bus.push_done(research_id, "failed", loop)
        _mark_failed(research_id, str(exc))

    finally:
        try:
            signal.alarm(0)
        except (AttributeError, OSError, ValueError):
            pass
        stream_bus.remove(research_id)


def _mark_failed(research_id: str, message: str) -> None:
    try:
        supabase.table("research_sessions").update({
            "status": "failed",
            "logs": [{
                "agent": "system",
                "status": "error",
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }).eq("id", research_id).execute()
    except Exception as inner:
        logger.error("failed_status_update_error", research_id=research_id, error=str(inner))


# ---------------------------------------------------------------------------
# POST /research/start
# ---------------------------------------------------------------------------

@router.post("/start", response_model=ResearchResponse)
async def start_research(
    body: StartResearchRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_user)],
    _rate: None = Depends(research_rate_limit),
) -> ResearchResponse:
    """
    Start a new research session. Requires a valid Supabase JWT.
    user_id is extracted from the token — never from the request body.
    Rate-limited to 10 research jobs per IP per hour.
    """
    user_id = current_user["user_id"]
    research_id = str(uuid.uuid4())

    try:
        supabase.table("research_sessions").insert({
            "id": research_id,
            "user_id": user_id,
            "topic": body.topic,
            "depth": body.depth,
            "status": "running",
            "logs": [],
            "sources": [],
            "is_complete": False,
        }).execute()
    except Exception as exc:
        logger.error("session_create_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to create session: {exc}")

    initial_state = ResearchState(
        topic=body.topic,
        depth=body.depth,
        research_id=research_id,
        user_override=None,
        plan=None,
        search_results=[],
        iteration=0,
        critique=None,
        synthesized_findings=None,
        report_sections=None,
        final_report=None,
        sources=[],
        overall_confidence=None,
        logs=[],
        token_usage=0,
        is_complete=False,
    )

    # Capture the running event loop before creating the queue so agents can
    # use it for streaming token events (synthesizer) and log events.
    loop = asyncio.get_event_loop()

    # Create the stream bus queue BEFORE starting the task so the SSE endpoint
    # can connect immediately without missing any events.
    stream_bus.create(research_id, loop)

    background_tasks.add_task(
        _run_research_graph,
        research_id,
        initial_state,
        loop,
        current_user.get("email", ""),
    )

    logger.info("session_started", research_id=research_id, user_id=user_id, topic=body.topic)
    return ResearchResponse(
        research_id=research_id,
        status="started",
        message=f"Research on '{body.topic}' has started.",
    )


# ---------------------------------------------------------------------------
# GET /research/{research_id}/stream  (SSE)
# ---------------------------------------------------------------------------

@router.get("/{research_id}/stream")
async def stream_research(
    research_id: str,
    current_user: Annotated[dict, Depends(get_current_user_query)],
) -> EventSourceResponse:
    """
    Server-Sent Events endpoint for real-time research progress.

    Primary path: reads from in-process asyncio.Queue (zero-lag, no polling).
    Fallback path: polls Supabase every 1.5s if the queue is unavailable
    (e.g. server restarted mid-job or client reconnected after disconnect).

    Auth: JWT passed as ?token=<jwt> query parameter.
    """
    session = _fetch_session(research_id)
    _assert_owner(session, current_user["user_id"])

    async def _queue_generator() -> AsyncGenerator[dict, None]:
        """Primary: deliver events from in-process queue with zero lag."""
        q = stream_bus.get(research_id)
        while True:
            try:
                # Wait up to 30s; yield a heartbeat to keep the connection alive
                item = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield {"event": "heartbeat", "data": "{}"}
                continue

            # Done sentinel
            if isinstance(item, dict) and item.get("__done__"):
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "type": "complete",
                        "research_id": research_id,
                        "status": item.get("status", "complete"),
                    }),
                }
                return

            # Streaming token from synthesizer (or any future streaming agent)
            if isinstance(item, dict) and item.get("__token__"):
                yield {
                    "event": "token",
                    "data": json.dumps({
                        "agent": item.get("agent", ""),
                        "text": item.get("text", ""),
                    }),
                }
                continue

            payload = {
                "research_id": research_id,
                "agent": item.get("agent", ""),
                "status": item.get("status", ""),
                "message": item.get("message", ""),
                "timestamp": item.get("timestamp", ""),
            }
            yield {"event": "log", "data": json.dumps(payload)}

    async def _poll_generator() -> AsyncGenerator[dict, None]:
        """Fallback: poll Supabase every 1.5s (used when queue is unavailable)."""
        sent_count = 0
        while True:
            try:
                row = (
                    supabase.table("research_sessions")
                    .select("logs, is_complete, status")
                    .eq("id", research_id)
                    .single()
                    .execute()
                )
                data = row.data or {}
                logs = data.get("logs") or []
                is_complete = data.get("is_complete", False)
                status = data.get("status", "running")

                for entry in logs[sent_count:]:
                    payload = {
                        "research_id": research_id,
                        "agent": entry.get("agent", ""),
                        "status": entry.get("status", ""),
                        "message": entry.get("message", ""),
                        "timestamp": entry.get("timestamp", ""),
                    }
                    yield {"event": "log", "data": json.dumps(payload)}

                sent_count = len(logs)

                if is_complete or status == "failed":
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "type": "complete",
                            "research_id": research_id,
                            "status": status,
                        }),
                    }
                    return

                await asyncio.sleep(_FALLBACK_POLL_INTERVAL)

            except Exception as exc:
                logger.error("sse_poll_error", research_id=research_id, error=str(exc))
                yield {"event": "error", "data": json.dumps({"error": str(exc)})}
                return

    # Use the fast queue path if available, otherwise fall back to polling
    generator = _queue_generator() if stream_bus.get(research_id) else _poll_generator()
    return EventSourceResponse(generator)


# ---------------------------------------------------------------------------
# POST /research/{research_id}/override
# ---------------------------------------------------------------------------

@router.post("/{research_id}/override", response_model=OverrideResponse)
async def override_research(
    research_id: str,
    body: OverrideRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> OverrideResponse:
    """Inject human guidance into a running session. Owner only."""
    session = _fetch_session(research_id)
    _assert_owner(session, current_user["user_id"])

    try:
        supabase.table("research_sessions").update({
            "user_override": body.message,
        }).eq("id", research_id).execute()

        logger.info("override_set", research_id=research_id, user_id=current_user["user_id"])
        return OverrideResponse(status="override_received")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("override_error", research_id=research_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to set override: {exc}")
