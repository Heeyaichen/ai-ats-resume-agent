"""Tests for Phase 7 Azure Function blob trigger.

Covers:
- Path parsing: valid paths, missing segments, wrong container.
- Metadata validation: match, mismatch, missing metadata.
- Job lookup: found, not found.
- Message body shape: {job_id, blob_path, jd_text}.
- Output binding integration: on_resume_upload.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.models.jobs import JobRecord, JobStatus
from backend.function_trigger.function_app import (
    parse_job_id_from_path,
    handle_blob_trigger,
)


def _make_job(job_id: str = "abc123") -> JobRecord:
    return JobRecord(
        id=job_id,
        status=JobStatus.QUEUED,
        filename="resume.pdf",
        blob_path=f"resumes-raw/{job_id}/resume.pdf",
        job_description="Python developer with 5 years experience",
        uploaded_by="test",
    )


def _get_job_factory(job: JobRecord | None) -> AsyncMock:
    """Create an async get_job callable returning the given job."""
    mock = AsyncMock(return_value=job)
    return mock


# ── Path parsing ──────────────────────────────────────────────────


class TestParseJobIdFromPath:
    def test_valid_path(self) -> None:
        assert parse_job_id_from_path("resumes-raw/job-42/resume.pdf") == "job-42"

    def test_valid_path_with_dots_in_filename(self) -> None:
        assert parse_job_id_from_path("resumes-raw/abc123/my.resume.v2.pdf") == "abc123"

    def test_backslash_path(self) -> None:
        assert parse_job_id_from_path("resumes-raw\\job-x\\resume.docx") == "job-x"

    def test_wrong_container(self) -> None:
        assert parse_job_id_from_path("reports/job-42/report.json") is None

    def test_too_short_path(self) -> None:
        assert parse_job_id_from_path("resumes-raw/file.pdf") is None

    def test_empty_path(self) -> None:
        assert parse_job_id_from_path("") is None

    def test_empty_job_id_segment(self) -> None:
        assert parse_job_id_from_path("resumes-raw//resume.pdf") is None


# ── handle_blob_trigger core logic ────────────────────────────────


class TestHandleBlobTrigger:
    @pytest.mark.asyncio
    async def test_valid_message_body(self) -> None:
        """Happy path: valid path, metadata match, job found."""
        job = _make_job("job-ok")
        get_job = _get_job_factory(job)

        result = await handle_blob_trigger(
            blob_path="job-ok/resume.pdf",
            blob_metadata={"job_id": "job-ok"},
            blob_uri="https://storage.blob.core.windows.net/resumes-raw/job-ok/resume.pdf",
            get_job=get_job,
        )

        assert result["job_id"] == "job-ok"
        assert result["blob_path"] == "resumes-raw/job-ok/resume.pdf"
        assert result["jd_text"] == "Python developer with 5 years experience"
        get_job.assert_awaited_once_with("job-ok")

    @pytest.mark.asyncio
    async def test_path_already_has_container_prefix(self) -> None:
        """Handles paths that already include resumes-raw/ prefix."""
        job = _make_job("prefixed")
        get_job = _get_job_factory(job)

        result = await handle_blob_trigger(
            blob_path="resumes-raw/prefixed/resume.pdf",
            blob_metadata={"job_id": "prefixed"},
            blob_uri="https://storage/resumes-raw/prefixed/resume.pdf",
            get_job=get_job,
        )

        assert result["job_id"] == "prefixed"
        assert result["blob_path"] == "resumes-raw/prefixed/resume.pdf"

    @pytest.mark.asyncio
    async def test_metadata_mismatch_raises(self) -> None:
        """Metadata job_id doesn't match path job_id -> ValueError."""
        with pytest.raises(ValueError, match="mismatch"):
            await handle_blob_trigger(
                blob_path="job-a/resume.pdf",
                blob_metadata={"job_id": "job-b"},
                blob_uri="https://storage/resumes-raw/job-a/resume.pdf",
                get_job=_get_job_factory(None),
            )

    @pytest.mark.asyncio
    async def test_missing_metadata_ok(self) -> None:
        """No metadata job_id is fine — we rely on the path."""
        job = _make_job("no-meta")
        get_job = _get_job_factory(job)

        result = await handle_blob_trigger(
            blob_path="no-meta/resume.pdf",
            blob_metadata={},
            blob_uri="https://storage/resumes-raw/no-meta/resume.pdf",
            get_job=get_job,
        )

        assert result["job_id"] == "no-meta"

    @pytest.mark.asyncio
    async def test_unparseable_path_raises(self) -> None:
        """Path that doesn't match resumes-raw/{job_id}/{name} -> ValueError."""
        with pytest.raises(ValueError, match="Cannot parse job_id"):
            await handle_blob_trigger(
                blob_path="just-a-file.pdf",
                blob_metadata={},
                blob_uri="https://storage/resumes-raw/just-a-file.pdf",
                get_job=_get_job_factory(None),
            )

    @pytest.mark.asyncio
    async def test_job_not_found_raises(self) -> None:
        """Job ID valid but not in Cosmos -> LookupError."""
        get_job = _get_job_factory(None)

        with pytest.raises(LookupError, match="not found"):
            await handle_blob_trigger(
                blob_path="missing-job/resume.pdf",
                blob_metadata={"job_id": "missing-job"},
                blob_uri="https://storage/resumes-raw/missing-job/resume.pdf",
                get_job=get_job,
            )


# ── Message shape validation ──────────────────────────────────────


class TestMessageShape:
    @pytest.mark.asyncio
    async def test_message_has_required_fields(self) -> None:
        """The Service Bus message must have job_id, blob_path, jd_text."""
        job = _make_job("shape-test")
        get_job = _get_job_factory(job)

        result = await handle_blob_trigger(
            blob_path="shape-test/resume.pdf",
            blob_metadata={"job_id": "shape-test"},
            blob_uri="https://storage/resumes-raw/shape-test/resume.pdf",
            get_job=get_job,
        )

        assert set(result.keys()) == {"job_id", "blob_path", "jd_text"}
        assert result["job_id"] == "shape-test"
        assert "shape-test" in result["blob_path"]
        assert result["jd_text"] == job.job_description


# ── Output binding integration ────────────────────────────────────


class TestOutputBinding:
    def test_on_resume_upload_sets_message(self) -> None:
        """The decorated function writes the correct JSON to the output binding."""
        from backend.function_trigger.function_app import on_resume_upload

        job = _make_job("binding-test")

        blob = MagicMock()
        blob.name = "resumes-raw/binding-test/resume.pdf"
        blob.metadata = {"job_id": "binding-test"}
        blob.trigger_metadata = {"job_id": "binding-test"}

        msg_out = MagicMock()

        with patch(
            "backend.function_trigger.function_app._get_job_and_build_message",
            new_callable=AsyncMock,
            return_value={
                "job_id": "binding-test",
                "blob_path": "resumes-raw/binding-test/resume.pdf",
                "jd_text": job.job_description,
            },
        ):
            on_resume_upload(blob=blob, msg=msg_out)

        msg_out.set.assert_called_once()
        sent = json.loads(msg_out.set.call_args[0][0])
        assert sent["job_id"] == "binding-test"
        assert sent["blob_path"] == "resumes-raw/binding-test/resume.pdf"
        assert sent["jd_text"] == job.job_description

    def test_on_resume_upload_skips_on_metadata_mismatch(self) -> None:
        """Metadata mismatch -> function returns without setting the output."""
        from backend.function_trigger.function_app import on_resume_upload

        blob = MagicMock()
        blob.name = "resumes-raw/job-a/resume.pdf"
        blob.metadata = {"job_id": "job-b"}
        blob.trigger_metadata = {"job_id": "job-a"}

        msg_out = MagicMock()

        on_resume_upload(blob=blob, msg=msg_out)
        msg_out.set.assert_not_called()

    def test_on_resume_upload_skips_on_missing_job(self) -> None:
        """Job not found in Cosmos -> function returns without setting output."""
        from backend.function_trigger.function_app import on_resume_upload

        blob = MagicMock()
        blob.name = "resumes-raw/gone-job/resume.pdf"
        blob.metadata = {"job_id": "gone-job"}
        blob.trigger_metadata = {"job_id": "gone-job"}

        msg_out = MagicMock()

        with patch(
            "backend.function_trigger.function_app._get_job_and_build_message",
            new_callable=AsyncMock,
            return_value=None,
        ):
            on_resume_upload(blob=blob, msg=msg_out)

        msg_out.set.assert_not_called()
