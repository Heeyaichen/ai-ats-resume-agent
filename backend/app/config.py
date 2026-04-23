"""Application configuration loaded from environment variables.

Uses pydantic-settings to read and validate all required configuration
at startup. The application must fail fast if any required value is
missing or malformed.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    """All runtime configuration. Values are read from environment variables
    or a `.env` file in the backend/ directory."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────
    app_name: str = "ats-agent"
    environment: Environment = Environment.DEV
    version: str = "0.1.0"
    log_level: str = "INFO"

    # ── Azure OpenAI ──────────────────────────────────────────────
    # Design spec Section 3.2: must fail at startup if endpoint
    # cannot resolve the expected deployments.
    azure_openai_endpoint: str = Field(
        ...,
        description="Azure OpenAI resource endpoint URL.",
    )
    azure_openai_key: str | None = Field(
        default=None,
        description="API key. Omit when using managed identity.",
    )
    chat_model_deployment_name: str = Field(
        default="gpt-4o",
        description="Deployment name for the chat/completions model.",
    )
    embedding_model_deployment_name: str = Field(
        default="text-embedding-ada-002",
        description="Deployment name for the embedding model.",
    )
    openai_api_version: str = "2024-06-01"

    # ── Azure AI Services ─────────────────────────────────────────
    document_intelligence_endpoint: str | None = None
    document_intelligence_key: str | None = None

    translator_endpoint: str | None = None
    translator_key: str | None = None
    translator_region: str | None = None

    language_endpoint: str | None = None
    language_key: str | None = None

    content_safety_endpoint: str | None = None
    content_safety_key: str | None = None

    # ── Azure Data ────────────────────────────────────────────────
    cosmos_endpoint: str | None = None
    cosmos_key: str | None = None
    cosmos_database_name: str = "ats-db"

    storage_connection_string: str | None = None
    storage_account_name: str | None = None

    redis_url: str | None = None
    redis_embedding_ttl_seconds: int = 3600  # 1 hour

    search_endpoint: str | None = None
    search_key: str | None = None
    search_index_name: str = "candidate-embeddings"

    # ── Azure Messaging ───────────────────────────────────────────
    servicebus_connection_string: str | None = None
    servicebus_queue_name: str = "ats-agent-jobs"

    # ── Security ──────────────────────────────────────────────────
    key_vault_url: str | None = None
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Allowed CORS origins, comma-separated.",
    )

    # ── Agent Runtime ─────────────────────────────────────────────
    agent_max_iterations: int = 12
    agent_max_retries_per_tool: int = 2

    # ── Upload Validation ─────────────────────────────────────────
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_jd_length: int = 50_000
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx")

    # ── Data Retention ────────────────────────────────────────────
    retention_days: int = 90


@lru_cache
def get_settings() -> Settings:
    """Cached accessor used across the application."""
    return Settings()
