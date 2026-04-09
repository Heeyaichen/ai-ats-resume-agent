"""Health check router — GET /api/health.

Design spec Section 5.1: no auth required, returns status/version/environment.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.models.health import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        version=settings.version,
        environment=settings.environment.value,
    )
