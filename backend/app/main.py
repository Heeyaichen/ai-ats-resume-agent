"""FastAPI application entrypoint.

Wires configuration, logging, lifespan events, routers, and app state.
Phase 5: health, upload, score, and SSE stream endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from backend.app.config import Settings
from backend.app.logging_config import configure_logging
from backend.app.routers.health import router as health_router
from backend.app.routers.score import SSERegistry
from backend.app.routers.score import router as score_router
from backend.app.routers.upload import router as upload_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup using settings stored on app.state."""
    settings: Settings = app.state.settings
    configure_logging(
        service=settings.app_name,
        environment=settings.environment.value,
        log_level=settings.log_level,
    )
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    When settings is None and AZURE_OPENAI_ENDPOINT is not set in the
    environment, a minimal test Settings is created so the app can
    start for health checks.
    """
    if settings is None:
        try:
            settings = Settings()
        except Exception:
            settings = Settings(
                azure_openai_endpoint="https://placeholder.openai.azure.com/",
            )

    app = FastAPI(
        title="ATS Resume Screening Agent",
        version=settings.version,
        lifespan=_lifespan,
    )

    # ── App state ──────────────────────────────────────────────
    app.state.settings = settings
    # In-memory fallback stores (used when adapters are unavailable).
    app.state.job_store: dict = {}
    app.state.score_store: dict = {}
    # SSE registry with Redis pub/sub for cross-process delivery.
    app.state.sse_registry = SSERegistry(redis_url=settings.redis_url)

    # ── Wire real Azure adapters ───────────────────────────────
    blob_adapter = None
    cosmos_adapter = None

    if settings.storage_connection_string:
        from backend.app.services.blob_storage import BlobStorageAdapter
        blob_adapter = BlobStorageAdapter(settings)

    if settings.cosmos_endpoint and settings.cosmos_key:
        from backend.app.services.cosmos import CosmosAdapter
        cosmos_adapter = CosmosAdapter(settings)

    app.state.blob_adapter = blob_adapter
    app.state.cosmos_adapter = cosmos_adapter

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(score_router)

    return app
