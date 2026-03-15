"""Simple in-process IP rate limiter implemented as a FastAPI dependency."""

from __future__ import annotations

from collections import defaultdict
from time import time
from typing import Callable

from fastapi import HTTPException, Request


def make_ip_rate_limiter(calls: int, seconds: int) -> Callable[[Request], None]:
    """
    Return a FastAPI dependency function that enforces a sliding-window rate
    limit keyed by client IP.

    Using a closure (plain function) rather than a callable class so that
    FastAPI correctly recognises `request: Request` as the special ASGI
    request object rather than a query parameter.

    Args:
        calls:   Maximum number of allowed calls within the window.
        seconds: Window length in seconds.

    Returns:
        A dependency function ``check(request: Request) -> None`` that raises
        HTTP 429 when the limit is exceeded.
    """
    log: dict[str, list[float]] = defaultdict(list)

    def check(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time()
        window_start = now - seconds
        bucket = log[ip]
        bucket[:] = [t for t in bucket if t > window_start]
        if len(bucket) >= calls:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )
        bucket.append(now)

    return check


# 10 research starts per IP per hour
research_rate_limit = make_ip_rate_limiter(calls=10, seconds=3600)
