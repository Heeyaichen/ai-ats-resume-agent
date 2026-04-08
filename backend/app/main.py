"""FastAPI application entrypoint.

The app factory wires configuration, logging, lifespan events, and
routers. Phase 2: minimal factory for test scaffolding with health endpoint.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from backend.app.config import Settings
from backend.app.logging_config import configure_logging
from backend.app.models.health import HealthResponse


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
    app.state.settings = settings

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        s: Settings = app.state.settings
        return HealthResponse(
            version=s.version,
            environment=s.environment.value,
        )

    return app
