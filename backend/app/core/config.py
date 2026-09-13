"""Application configuration.

All configuration is sourced from environment variables (or an optional
`.env` file) via pydantic-settings. Secrets are never hard-coded; see
`.env.example` for the full list of supported variables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Optional[Path]:
    """Find the repo root (dir containing both backend/ and frontend/).

    Returns None in stripped-down deployments (e.g. the Docker image, which
    contains only the backend) so callers fall back to a relative path.
    """
    for p in Path(__file__).resolve().parents:
        if (p / "backend").is_dir() and (p / "frontend").is_dir():
            return p
    return None


def _anchored(sub: str) -> str:
    root = _project_root()
    return str(root / sub) if root else sub


class Settings(BaseSettings):
    """Typed application settings.

    Values are read from the process environment. A local `.env` file is
    loaded automatically for development convenience but should never contain
    production secrets that are committed to source control.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ app
    PROJECT_NAME: str = "EduIntel"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    # Comma-separated list of allowed CORS origins.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    # --------------------------------------------------------------- security
    # Used to sign tokens / audit records. Override in every real deployment.
    SECRET_KEY: str = "change-me-in-production"
    # When set, protected endpoints require this key via the `X-API-Key`
    # header. Left empty in development so the demo works out of the box.
    API_KEY: Optional[str] = None

    # -------------------------------------------------------------- database
    POSTGRES_USER: str = "eduintel"
    POSTGRES_PASSWORD: str = "eduintel"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eduintel"
    # If provided, DATABASE_URL wins over the discrete POSTGRES_* fields.
    DATABASE_URL: Optional[str] = None

    # ---------------------------------------------------------------- LLM/RAG
    # Provider abstraction: the application is never coupled to one vendor.
    LLM_PROVIDER: Literal["gemini", "openai", "local"] = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Generation controls used by every provider.
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # Embeddings are always local (sentence-transformers) for reproducibility
    # and zero-cost operation; RAG works fully offline.
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.25

    # --------------------------------------------------------------- ml/data
    RANDOM_SEED: int = 42
    # Anchored to the repo root so training (run from the root) and the API
    # (run from backend/) resolve to the same directory. Overridable via env.
    DATA_DIR: str = Field(default_factory=lambda: _anchored("data"))
    MODEL_DIR: str = Field(default_factory=lambda: _anchored("models"))
    ACTIVE_MODEL_STATUS: str = "active"

    # Directory of the built frontend to serve in production (single-service
    # deploy). Empty in local dev, where the Vite dev server serves the SPA.
    FRONTEND_DIST: str = ""

    # ---------------------------------------------------------------- derived
    @property
    def sqlalchemy_database_uri(self) -> str:
        url = self.DATABASE_URL
        if url:
            # Managed hosts (Render, Heroku, Railway) hand out a "postgres://"
            # URL that SQLAlchemy 2.0 rejects; normalise to the psycopg2 driver.
            if url.startswith("postgres://"):
                url = "postgresql+psycopg2://" + url[len("postgres://"):]
            elif url.startswith("postgresql://"):
                url = "postgresql+psycopg2://" + url[len("postgresql://"):]
            return url
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("EMBEDDING_DIM")
    @classmethod
    def _dim_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("EMBEDDING_DIM must be positive")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()


settings = get_settings()
