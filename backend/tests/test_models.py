"""Tests for domain models — validation and defaults."""

from __future__ import annotations

import pytest

from backend.app.models.jobs import JobRecord, JobStatus, UploadResponse
from backend.app.models.candidates import CandidateRecord
from backend.app.models.scores import ScoreBreakdown, ScoreRecord
from backend.app.models.traces import AgentTraceRecord, TraceStep
from backend.app.models.reviews import ReviewFlag, ReviewSeverity, ReviewCreator
from backend.app.models.events import (
    AgentEventType,
    ToolCallEvent,
    ToolResultEvent,
    CompleteEvent,
    ErrorEvent,
)
from backend.app.models.health import HealthResponse


class TestJobRecord:
    def test_default_status_is_queued(self) -> None:
        job = JobRecord(
            filename="resume.pdf",
            blob_path="resumes-raw/abc/resume.pdf",
            job_description="Python developer",
            uploaded_by="user@example.com",
        )
        assert job.status == JobStatus.QUEUED
        assert job.retention_hold is False
        assert job.id  # auto-generated

    def test_upload_response(self) -> None:
        resp = UploadResponse(job_id="abc123")
        assert resp.status == JobStatus.QUEUED


class TestScoreRecord:
    def test_breakdown_weights(self) -> None:
        breakdown = ScoreBreakdown(
            keyword_match=35,
            experience_alignment=25,
            skills_coverage=20,
        )
        assert breakdown.keyword_match + breakdown.experience_alignment + breakdown.skills_coverage == 80

    def test_score_bounds(self) -> None:
        score = ScoreRecord(
            job_id="j1",
            score=85,
            breakdown=ScoreBreakdown(keyword_match=34, experience_alignment=26, skills_coverage=25),
        )
        assert 0 <= score.score <= 100

    def test_score_rejects_over_100(self) -> None:
        with pytest.raises(Exception):
            ScoreRecord(
                job_id="j1",
                score=150,
                breakdown=ScoreBreakdown(keyword_match=50, experience_alignment=50, skills_coverage=50),
            )

    def test_breakdown_rejects_out_of_range(self) -> None:
        with pytest.raises(Exception):
            ScoreBreakdown(keyword_match=41, experience_alignment=0, skills_coverage=0)


class TestAgentTraceRecord:
    def test_contains_raw_text_always_false(self) -> None:
        trace = AgentTraceRecord(job_id="j1")
        assert trace.contains_raw_text is False

    def test_trace_steps(self) -> None:
        step = TraceStep(
            iteration=1,
            tool_name="extract_resume_text",
            arguments_summary="resume blob path",
            result_summary="Extracted 2 pages",
            duration_ms=1200,
        )
        trace = AgentTraceRecord(job_id="j1", steps=[step], total_iterations=1)
        assert len(trace.steps) == 1
        assert trace.steps[0].tool_name == "extract_resume_text"


class TestReviewFlag:
    def test_default_creator_is_agent(self) -> None:
        flag = ReviewFlag(job_id="j1", reason_code="low_score", reason="Score 25")
        assert flag.created_by == ReviewCreator.AGENT
        assert flag.severity == ReviewSeverity.MEDIUM


class TestSSEEvents:
    def test_tool_call_event_type(self) -> None:
        event = ToolCallEvent(
            job_id="j1",
            iteration=1,
            tool_name="extract_resume_text",
            arguments_summary="resume blob path",
        )
        assert event.event_type == AgentEventType.TOOL_CALL
        assert event.timestamp

    def test_tool_result_event(self) -> None:
        event = ToolResultEvent(
            job_id="j1",
            iteration=1,
            tool_name="extract_resume_text",
            result_summary="Extracted 2 pages",
            duration_ms=1500,
        )
        assert event.event_type == AgentEventType.TOOL_RESULT

    def test_complete_event(self) -> None:
        event = CompleteEvent(job_id="j1", result={"score": 85})
        assert event.event_type == AgentEventType.COMPLETE

    def test_error_event(self) -> None:
        event = ErrorEvent(job_id="j1", message="Tool failed", retryable=True)
        assert event.event_type == AgentEventType.ERROR
        assert event.retryable is True

    def test_all_events_have_timestamp_and_job_id(self) -> None:
        for event in [
            ToolCallEvent(job_id="j1", iteration=1, tool_name="t", arguments_summary="a"),
            ToolResultEvent(job_id="j2", iteration=1, tool_name="t", result_summary="r", duration_ms=1),
            CompleteEvent(job_id="j3"),
            ErrorEvent(job_id="j4", message="err"),
        ]:
            assert event.job_id
            assert event.timestamp


class TestCandidateRecord:
    def test_defaults(self) -> None:
        rec = CandidateRecord(job_id="j1", resume_blob_path="resumes-raw/j1/resume.pdf")
        assert rec.translated is False
        assert rec.pii_detected is False


class TestHealthResponse:
    def test_fields(self) -> None:
        resp = HealthResponse(version="0.1.0", environment="dev")
        assert resp.status == "ok"
