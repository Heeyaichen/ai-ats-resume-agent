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
    # In-memory stores for Phase 5. Phase 6 will wire Cosmos/Blob.
    app.state.job_store: dict = {}
    app.state.score_store: dict = {}
    app.state.sse_registry = SSERegistry()
    # Optional adapters — set by tests or Phase 6 worker wiring.
    app.state.blob_adapter = None
    app.state.cosmos_adapter = None

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(score_router)

    return app
