"""Tests for the FastAPI app factory and health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "environment" in body

    def test_health_no_auth_required(self) -> None:
        """Health endpoint is unauthenticated per design spec Section 5.1."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
