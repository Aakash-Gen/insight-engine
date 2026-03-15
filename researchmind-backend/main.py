"""ResearchMind FastAPI application entry point."""

from __future__ import annotations

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging_config import configure_logging

# Configure structured logging before anything else imports logging
configure_logging()
logger = structlog.get_logger(__name__)

# Sentry — only active when SENTRY_DSN is set in .env
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.2,   # 20% of requests traced for performance
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
    )
    logger.info("sentry_initialized", dsn_set=True, environment=settings.ENVIRONMENT)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "startup",
        provider=settings.LLM_PROVIDER,
        model=settings.active_model,
        max_iterations=settings.MAX_RESEARCH_ITERATIONS,
        environment=settings.ENVIRONMENT,
    )
    yield
    logger.info("shutdown")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ResearchMind API",
    description="Multi-agent AI research platform powered by LangGraph + Claude.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — use allow_origins=["*"] with allow_credentials=False so that
# Starlette doesn't reject preflight with 400 (CORS spec forbids wildcard
# origin + credentials=true). The frontend authenticates via Bearer tokens
# in the Authorization header, not cookies, so credentials=False is correct.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (imported after app creation to avoid circular imports)
from api.routes.research import router as research_router    # noqa: E402
from api.routes.reports import router as reports_router      # noqa: E402
from api.routes.templates import router as templates_router  # noqa: E402

app.include_router(research_router)
app.include_router(reports_router)
app.include_router(templates_router)


# ---------------------------------------------------------------------------
# Stub for browser-extension polling (silences 404 noise in dev logs)
# ---------------------------------------------------------------------------

@app.get("/alerts/unread-count", tags=["meta"], include_in_schema=False)
async def alerts_stub() -> dict:
    return {"count": 0}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health_check() -> dict:
    """
    Deep health check: verifies Supabase connectivity in addition to
    reporting the active LLM provider and model.
    """
    from core.supabase_client import supabase

    db_ok = False
    try:
        # Lightweight ping — select a single row (table may be empty)
        supabase.table("research_sessions").select("id").limit(1).execute()
        db_ok = True
    except Exception as exc:
        logger.warning("health_check_db_fail", error=str(exc))

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "provider": settings.LLM_PROVIDER,
        "model": settings.active_model,
        "db": "ok" if db_ok else "unreachable",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
