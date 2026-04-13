"""
LiRA Backend — Core Configuration
Environment-driven settings using pydantic-settings.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    APP_NAME: str = "LiRA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Server ───────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://lira:lira_secret@localhost:5432/lira"
    DATABASE_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT Auth ─────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE-ME-TO-A-REAL-SECRET-KEY-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Google OAuth 2.0 ─────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_SCOPES: str = "openid email profile"

    # ── LLM Configuration (preserved from existing pipeline) ─
    LLM_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── External APIs (preserved) ────────────────────────────
    SERPAPI_API_KEY: str = ""
    CHATPDF_API_KEY: str = ""

    # ── Storage ──────────────────────────────────────────────
    STORAGE_BACKEND: str = "local"  # local | s3
    STORAGE_LOCAL_ROOT: str = "./storage"
    S3_BUCKET_NAME: str = ""
    S3_ENDPOINT_URL: str = ""  # For R2: https://<account>.r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "auto"

    # ── Frontend URL (for OAuth redirect after login) ────────
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def google_scopes_list(self) -> List[str]:
        return [s.strip() for s in self.GOOGLE_SCOPES.split() if s.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
