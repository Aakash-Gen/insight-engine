"""Application configuration loaded from environment variables."""

from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic settings model for all environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider — "anthropic", "xai", or "groq"
    LLM_PROVIDER: Literal["anthropic", "xai", "groq"] = "groq"

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # xAI (Grok)
    XAI_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-3"

    # Groq (fast inference, generous free tier)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Tavily
    TAVILY_API_KEY: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_DB_URL: str = ""
    # JWT secret from Supabase Dashboard → Settings → API → JWT Settings
    SUPABASE_JWT_SECRET: str = ""

    # Research settings
    MAX_RESEARCH_ITERATIONS: int = 2
    MAX_SEARCH_RESULTS: int = 8
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # CORS — stored as a comma-separated string; use the cors_origins property
    # in application code. pydantic-settings requires JSON for List fields;
    # a plain string avoids that source-level parse error.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Observability
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "1.0.0"

    # Job settings
    RESEARCH_TIMEOUT_SECONDS: int = 600  # 10 minutes

    # Email notifications (optional — leave blank to disable)
    # Option A: Resend (https://resend.com) — recommended
    RESEND_API_KEY: str = ""
    # Option B: SMTP fallback (used when RESEND_API_KEY is not set)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    # Sender address used for both Resend and SMTP
    NOTIFY_FROM_EMAIL: str = "noreply@researchmind.io"

    @property
    def cors_origins(self) -> List[str]:
        """Return CORS origins as a list (split on commas)."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def active_model(self) -> str:
        """Return the active model name based on the selected provider."""
        if self.LLM_PROVIDER == "xai":
            return self.GROK_MODEL
        if self.LLM_PROVIDER == "groq":
            return self.GROQ_MODEL
        return self.CLAUDE_MODEL


settings = Settings()
