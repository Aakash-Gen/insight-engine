"""
Structured JSON logging via structlog.

Call configure_logging() once at app startup. After that, use:

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("event_name", research_id="...", agent="planner", tokens=42)

All log lines are emitted as JSON to stdout, compatible with Railway, Render,
Fly.io, and log aggregation services (Datadog, Loki, CloudWatch).

Stdlib loggers (uvicorn, httpx, supabase) are bridged through structlog's
foreign pre-chain so they appear in the same JSON stream.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output and stdlib bridge."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Processors shared by both structlog native loggers and stdlib bridge
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib loggers (uvicorn, httpx, etc.) into the same JSON stream
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=shared_processors + [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            foreign_pre_chain=shared_processors,
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
