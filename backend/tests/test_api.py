"""Tests for Phase 5 API endpoints.

Covers design spec Section 13.3 required API tests:
- Reject unsupported file type.
- Reject oversized file.
- Create deterministic blob path with job_id.
- Create jobs document on upload.
- Return score when available.
- Return queued/running state before score is available.
- Format SSE events as valid data: {json}\\n\\n.
- Emit terminal error event when worker fails.
"""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.jobs import JobRecord, JobStatus


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def _make_upload(file_name: str = "resume.pdf", content: bytes = b"%PDF-1.4 fake", jd: str = "Python developer"):
    """Helper to build upload multipart data."""
    return {
        "file": (file_name, io.BytesIO(content), "application/pdf"),
        "job_description": (None, jd),
    }


# ── Upload validation ──────────────────────────────────────────


class TestUploadValidation:
    def test_reject_unsupported_file_type(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files=_make_upload(file_name="resume.exe"))
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]

    def test_reject_oversized_file(self, client: TestClient) -> None:
        big = b"x" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte
        resp = client.post("/api/upload", files=_make_upload(content=big))
        assert resp.status_code == 400
        assert "exceeds" in resp.json()["detail"].lower()

    def test_reject_empty_jd(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files={
            "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
            "job_description": (None, "   "),
        })
        assert resp.status_code == 400

    def test_reject_oversized_jd(self, client: TestClient) -> None:
        long_jd = "x" * 50_001
        resp = client.post("/api/upload", files={
            "file": ("resume.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
            "job_description": (None, long_jd),
        })
        assert resp.status_code == 400
        assert "50000" in resp.json()["detail"]


# ── Upload success ──────────────────────────────────────────────


class TestUploadSuccess:
    def test_upload_returns_job_id_and_queued(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files=_make_upload())
        assert resp.status_code == 200
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "queued"
        assert len(body["job_id"]) == 32  # uuid4 hex

    def test_upload_creates_job_in_store(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files=_make_upload())
        job_id = resp.json()["job_id"]
        job: JobRecord = client.app.state.job_store[job_id]
        assert job.id == job_id
        assert job.status == JobStatus.QUEUED
        assert job.blob_path.startswith("resumes-raw/")

    def test_blob_path_contains_job_id(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files=_make_upload())
        job_id = resp.json()["job_id"]
        job = client.app.state.job_store[job_id]
        assert f"resumes-raw/{job_id}/" in job.blob_path

    def test_upload_docx(self, client: TestClient) -> None:
        resp = client.post("/api/upload", files={
            "file": ("resume.docx", io.BytesIO(b"PK\x03\x04"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "job_description": (None, "Developer"),
        })
        assert resp.status_code == 200


# ── Score retrieval ─────────────────────────────────────────────


class TestGetScore:
    def test_404_for_unknown_job(self, client: TestClient) -> None:
        resp = client.get("/api/score/nonexistent")
        assert resp.status_code == 404

    def test_returns_queued_status_before_scoring(self, client: TestClient) -> None:
        upload_resp = client.post("/api/upload", files=_make_upload())
        job_id = upload_resp.json()["job_id"]

        score_resp = client.get(f"/api/score/{job_id}")
        assert score_resp.status_code == 200
        body = score_resp.json()
        assert body["status"] == "queued"
        assert body["job_id"] == job_id

    def test_returns_score_when_available(self, client: TestClient) -> None:
        upload_resp = client.post("/api/upload", files=_make_upload())
        job_id = upload_resp.json()["job_id"]

        client.app.state.score_store[job_id] = {
            "score": 85,
            "breakdown": {"keyword_match": 35, "experience_alignment": 25, "skills_coverage": 25},
            "matched_keywords": ["python"],
            "missing_keywords": ["azure"],
            "semantic_similarity": 0.88,
            "fit_summary": "Strong candidate.",
        }
        job: JobRecord = client.app.state.job_store[job_id]
        job.status = JobStatus.COMPLETED

        score_resp = client.get(f"/api/score/{job_id}")
        assert score_resp.status_code == 200
        body = score_resp.json()
        assert body["status"] == "completed"
        assert body["score_data"]["score"] == 85


# ── SSE stream ──────────────────────────────────────────────────


class TestSSEStream:
    def test_404_for_unknown_job_stream(self, client: TestClient) -> None:
        resp = client.get("/api/score/nonexistent/stream")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_sse_valid_framing(self) -> None:
        """Verify SSE events use valid data: {json}\\n\\n framing via async client."""
        import asyncio
        import httpx

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            # Upload a job.
            upload_resp = await ac.post(
                "/api/upload",
                files={"file": ("resume.pdf", b"%PDF", "application/pdf")},
                data={"job_description": "Python dev"},
            )
            job_id = upload_resp.json()["job_id"]
            registry = app.state.sse_registry

            # Schedule an event to be emitted after a short delay.
            async def emit_complete():
                await asyncio.sleep(0.1)
                await registry.emit(job_id, {
                    "event_type": "complete",
                    "job_id": job_id,
                    "result": {"score": 80},
                })

            asyncio.create_task(emit_complete())

            # Consume SSE stream.
            async with ac.stream("GET", f"/api/score/{job_id}/stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        payload = json.loads(line[6:])
                        assert "event_type" in payload
                        assert "job_id" in payload
                        assert payload["event_type"] == "complete"
                        break

    @pytest.mark.asyncio
    async def test_sse_error_event(self) -> None:
        """SSE stream emits error event."""
        import asyncio
        import httpx

        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            upload_resp = await ac.post(
                "/api/upload",
                files={"file": ("resume.pdf", b"%PDF", "application/pdf")},
                data={"job_description": "Dev"},
            )
            job_id = upload_resp.json()["job_id"]
            registry = app.state.sse_registry

            async def emit_error():
                await asyncio.sleep(0.1)
                await registry.emit(job_id, {
                    "event_type": "error",
                    "job_id": job_id,
                    "message": "Job failed.",
                })

            asyncio.create_task(emit_error())

            async with ac.stream("GET", f"/api/score/{job_id}/stream") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        payload = json.loads(line[6:])
                        assert payload["event_type"] == "error"
                        assert "failed" in payload["message"].lower()
                        break


# ── Health endpoint ─────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "environment" in body
