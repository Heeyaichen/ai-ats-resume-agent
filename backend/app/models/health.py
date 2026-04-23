"""Health check response — GET /api/health.

Design spec Section 5.1: auth not required, returns status/version/environment.
"""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
