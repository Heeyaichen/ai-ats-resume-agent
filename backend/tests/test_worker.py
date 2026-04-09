"""Tests for Phase 6 Service Bus worker.

Covers:
- Message validation (missing fields).
- Job not found in store.
- Successful agent run → completed status, score persisted, trace persisted.
- Agent run with review flag → completed_with_review status.
- Agent run with error → failed_review_required status.
- Retryable failure → abandon (returns False).
- Non-retryable failure → dead-letter (returns True, review flag written).
- Max deliveries exceeded → dead-letter.
- SSE events emitted during run.
- run_worker with async iterator message source.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_runner import AgentResult
from backend.app.config import Settings
from backend.app.models.jobs import JobRecord, JobStatus
from backend.app.models.reviews import ReviewFlag
from backend.app.routers.score import SSERegistry
from backend.app.worker import (
    process_message,
    process_message_with_retry,
    run_worker,
    _build_score_record,
    _determine_final_status,
    _is_retryable,
)


def _make_settings() -> Settings:
    return Settings(azure_openai_endpoint="https://placeholder.openai.azure.com/")


def _make_job(job_id: str = "test-job-123") -> JobRecord:
    return JobRecord(
        id=job_id,
        status=JobStatus.QUEUED,
        filename="resume.pdf",
        blob_path=f"resumes-raw/{job_id}/resume.pdf",
        job_description="Python developer with 5 years experience",
        uploaded_by="test",
    )


def _make_message(job_id: str = "test-job-123") -> dict[str, Any]:
    return {
        "job_id": job_id,
        "blob_path": f"resumes-raw/{job_id}/resume.pdf",
        "jd_text": "Python developer with 5 years experience",
    }


def _make_stores() -> dict[str, Any]:
    return {
        "job_store": {},
        "score_store": {},
        "trace_store": {},
        "review_store": {},
    }


def _make_runner_factory(result: AgentResult) -> Any:
    """Create a factory that returns a mock runner producing the given result."""
    runner = AsyncMock()
    runner.run = AsyncMock(return_value=result)
    return lambda _settings: runner


# ── Status determination ──────────────────────────────────────────


class TestDetermineFinalStatus:
    def test_completed(self) -> None:
        result = AgentResult(job_id="x")
        assert _determine_final_status(result) == JobStatus.COMPLETED

    def test_completed_with_review(self) -> None:
        result = AgentResult(job_id="x", human_review_required=True, human_review_reason="Low score")
        assert _determine_final_status(result) == JobStatus.COMPLETED_WITH_REVIEW

    def test_failed_review_required(self) -> None:
        result = AgentResult(job_id="x", error="Agent crashed")
        assert _determine_final_status(result) == JobStatus.FAILED_REVIEW_REQUIRED


# ── Score record building ─────────────────────────────────────────


class TestBuildScoreRecord:
    def test_returns_none_when_no_score(self) -> None:
        result = AgentResult(job_id="x")
        assert _build_score_record("x", result) is None

    def test_builds_score_dict(self) -> None:
        result = AgentResult(
            job_id="x",
            score=75,
            breakdown={"keyword_match": 30, "experience_alignment": 25, "skills_coverage": 20},
            matched_keywords=["python"],
            missing_keywords=["azure"],
            semantic_similarity=0.85,
            fit_summary="Good candidate.",
            similar_candidates=[{"candidate_id": "c1"}],
        )
        score = _build_score_record("x", result)
        assert score is not None
        assert score["score"] == 75
        assert score["breakdown"]["keyword_match"] == 30
        assert score["matched_keywords"] == ["python"]
        assert score["semantic_similarity"] == 0.85
        assert len(score["similar_candidates"]) == 1


# ── Retryable check ───────────────────────────────────────────────


class TestIsRetryable:
    def test_timeout_is_retryable(self) -> None:
        assert _is_retryable(Exception("Connection timeout")) is True

    def test_503_is_retryable(self) -> None:
        assert _is_retryable(Exception("Service returned 503")) is True

    def test_value_error_not_retryable(self) -> None:
        assert _is_retryable(ValueError("Invalid message")) is False

    def test_throttle_is_retryable(self) -> None:
        assert _is_retryable(Exception("Rate limited: throttling")) is True


# ── Message validation ────────────────────────────────────────────


class TestMessageValidation:
    @pytest.mark.asyncio
    async def test_missing_job_id(self) -> None:
        stores = _make_stores()
        with pytest.raises(ValueError, match="missing"):
            await process_message(
                {"blob_path": "x", "jd_text": "y"},
                settings=_make_settings(),
                sse_registry=SSERegistry(),
                **stores,
            )

    @pytest.mark.asyncio
    async def test_missing_blob_path(self) -> None:
        stores = _make_stores()
        with pytest.raises(ValueError, match="missing"):
            await process_message(
                {"job_id": "x", "jd_text": "y"},
                settings=_make_settings(),
                sse_registry=SSERegistry(),
                **stores,
            )

    @pytest.mark.asyncio
    async def test_missing_jd_text(self) -> None:
        stores = _make_stores()
        with pytest.raises(ValueError, match="missing"):
            await process_message(
                {"job_id": "x", "blob_path": "y"},
                settings=_make_settings(),
                sse_registry=SSERegistry(),
                **stores,
            )


# ── Job not found ─────────────────────────────────────────────────


class TestJobNotFound:
    @pytest.mark.asyncio
    async def test_job_not_in_store_raises(self) -> None:
        stores = _make_stores()
        with pytest.raises(ValueError, match="not found"):
            await process_message(
                _make_message("nonexistent"),
                settings=_make_settings(),
                sse_registry=SSERegistry(),
                **stores,
            )


# ── Successful processing ─────────────────────────────────────────


class TestSuccessfulProcessing:
    @pytest.mark.asyncio
    async def test_completed_status(self) -> None:
        job_id = "job-ok"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job
        registry = SSERegistry()

        result = AgentResult(job_id=job_id, score=85)
        factory = _make_runner_factory(result)

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=registry,
            agent_runner_factory=factory,
            **stores,
        )

        assert job.status == JobStatus.COMPLETED
        assert stores["score_store"][job_id]["score"] == 85

    @pytest.mark.asyncio
    async def test_trace_persisted(self) -> None:
        job_id = "job-trace"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result = AgentResult(job_id=job_id, score=90, total_iterations=5, total_duration_ms=3000)
        factory = _make_runner_factory(result)

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert job_id in stores["trace_store"]
        trace = stores["trace_store"][job_id]
        assert trace.job_id == job_id

    @pytest.mark.asyncio
    async def test_status_updated_to_agent_running_during_run(self) -> None:
        """Verify job status is set to agent_running before the runner executes."""
        job_id = "job-running"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        statuses_seen: list[JobStatus] = []

        async def mock_run(memory: AgentMemory, **kwargs: Any) -> AgentResult:
            statuses_seen.append(job.status)
            return AgentResult(job_id=job_id, score=80)

        runner = AsyncMock()
        runner.run = mock_run
        factory = lambda _s: runner

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert JobStatus.AGENT_RUNNING in statuses_seen
        assert job.status == JobStatus.COMPLETED


# ── Review flag handling ──────────────────────────────────────────


class TestReviewFlagHandling:
    @pytest.mark.asyncio
    async def test_completed_with_review(self) -> None:
        job_id = "job-review"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result = AgentResult(
            job_id=job_id,
            score=25,
            human_review_required=True,
            human_review_reason="Low score.",
        )
        factory = _make_runner_factory(result)

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert job.status == JobStatus.COMPLETED_WITH_REVIEW
        assert job_id in stores["review_store"]
        assert len(stores["review_store"][job_id]) == 1
        assert stores["review_store"][job_id][0].reason == "Low score."

    @pytest.mark.asyncio
    async def test_failed_review_required_on_error(self) -> None:
        job_id = "job-error"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result = AgentResult(
            job_id=job_id,
            error="Agent crashed",
            human_review_required=True,
            human_review_reason="Agent run failed: Agent crashed",
        )
        factory = _make_runner_factory(result)

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert job.status == JobStatus.FAILED_REVIEW_REQUIRED
        assert job_id in stores["review_store"]


# ── SSE event emission ────────────────────────────────────────────


class TestSSEEvents:
    @pytest.mark.asyncio
    async def test_events_emitted_via_callback(self) -> None:
        """Verify the runner receives an event_callback that emits to SSE."""
        job_id = "job-sse"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job
        registry = SSERegistry()

        events_received: list[dict] = []

        async def mock_run(memory: AgentMemory, *, event_callback: Any = None, **kw: Any) -> AgentResult:
            if event_callback:
                await event_callback({"event_type": "tool_call", "job_id": job_id})
            return AgentResult(job_id=job_id, score=80)

        runner = AsyncMock()
        runner.run = mock_run
        factory = lambda _s: runner

        # Register a queue to capture SSE events.
        queue = registry.register(job_id)

        await process_message(
            _make_message(job_id),
            settings=_make_settings(),
            sse_registry=registry,
            agent_runner_factory=factory,
            **stores,
        )

        # The SSE event should be in the queue.
        payload = queue.get_nowait()
        import json
        event = json.loads(payload)
        assert event["event_type"] == "tool_call"
        assert event["job_id"] == job_id


# ── Retry / dead-letter logic ─────────────────────────────────────


class TestRetryDeadLetter:
    @pytest.mark.asyncio
    async def test_retryable_failure_abandons(self) -> None:
        """Retryable error on first delivery → return False (abandon)."""
        job_id = "retry-job"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        # Factory that raises a retryable error.
        runner = AsyncMock()
        runner.run = AsyncMock(side_effect=Exception("Connection timeout"))
        factory = lambda _s: runner

        result = await process_message_with_retry(
            _make_message(job_id),
            delivery_count=1,
            max_deliveries=3,
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )
        assert result is False  # abandon

    @pytest.mark.asyncio
    async def test_non_retryable_failure_dead_letters(self) -> None:
        """Non-retryable error → dead-letter (return True)."""
        job_id = "nonretry-job"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        # Factory that raises a non-retryable error.
        runner = AsyncMock()
        runner.run = AsyncMock(side_effect=ValueError("Bad data"))
        factory = lambda _s: runner

        result = await process_message_with_retry(
            _make_message(job_id),
            delivery_count=1,
            max_deliveries=3,
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert result is True  # dead-letter
        assert job.status == JobStatus.FAILED_REVIEW_REQUIRED
        assert job_id in stores["review_store"]
        flag = stores["review_store"][job_id][0]
        assert flag.reason_code == "worker_dead_letter"

    @pytest.mark.asyncio
    async def test_max_deliveries_exceeded_dead_letters(self) -> None:
        """Retryable error at max delivery count → dead-letter."""
        job_id = "max-del-job"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result = await process_message_with_retry(
            _make_message(job_id),
            delivery_count=3,  # at max
            max_deliveries=3,
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            **stores,
        )

        assert result is True  # dead-letter
        assert job.status == JobStatus.FAILED_REVIEW_REQUIRED

    @pytest.mark.asyncio
    async def test_successful_run_completes(self) -> None:
        """Successful run → return True (complete)."""
        job_id = "ok-job"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result_agent = AgentResult(job_id=job_id, score=90)
        factory = _make_runner_factory(result_agent)

        result = await process_message_with_retry(
            _make_message(job_id),
            delivery_count=1,
            max_deliveries=3,
            settings=_make_settings(),
            sse_registry=SSERegistry(),
            agent_runner_factory=factory,
            **stores,
        )

        assert result is True  # complete


# ── run_worker with async iterator ────────────────────────────────


class TestRunWorker:
    @pytest.mark.asyncio
    async def test_processes_async_iterator(self) -> None:
        """run_worker consumes messages from an async iterator."""
        job_id = "worker-job"
        job = _make_job(job_id)
        stores = _make_stores()
        stores["job_store"][job_id] = job

        result_agent = AgentResult(job_id=job_id, score=88)
        factory = _make_runner_factory(result_agent)

        async def message_source():
            yield _make_message(job_id), 1

        await run_worker(
            _make_settings(),
            agent_runner_factory=factory,
            message_source=message_source(),
            sse_registry=SSERegistry(),
            **stores,
        )

        assert job.status == JobStatus.COMPLETED
        assert stores["score_store"][job_id]["score"] == 88

    @pytest.mark.asyncio
    async def test_processes_multiple_messages(self) -> None:
        """run_worker processes all messages from the iterator."""
        stores = _make_stores()
        for i in range(3):
            job_id = f"multi-job-{i}"
            stores["job_store"][job_id] = _make_job(job_id)

        result_agent = AgentResult(job_id="any", score=50)
        factory = _make_runner_factory(result_agent)

        async def message_source():
            for i in range(3):
                job_id = f"multi-job-{i}"
                yield _make_message(job_id), 1

        await run_worker(
            _make_settings(),
            agent_runner_factory=factory,
            message_source=message_source(),
            sse_registry=SSERegistry(),
            **stores,
        )

        for i in range(3):
            job_id = f"multi-job-{i}"
            assert stores["job_store"][job_id].status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_production_mode_raises_without_connection_string(self) -> None:
        """run_worker without message_source requires connection string."""
        with pytest.raises(RuntimeError, match="SERVICEBUS_CONNECTION_STRING"):
            await run_worker(
                _make_settings(),
                job_store={},
                score_store={},
                trace_store={},
                review_store={},
                sse_registry=SSERegistry(),
            )
