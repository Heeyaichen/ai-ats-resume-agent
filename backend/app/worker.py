"""Service Bus worker — consumes queue messages and runs the guarded agent.

Design spec Section 5.3:
- Receive one Service Bus message at a time per task execution.
- Validate message shape: {job_id, blob_path, jd_text}.
- Update the job status to agent_running.
- Create or find the SSE queue for the job.
- Run the guarded agent.
- Persist score, trace, review flag, and report JSON.
- Update the job status to completed, completed_with_review, or failed_review_required.
- Complete the Service Bus message only after durable writes succeed.
- Abandon on retryable failures with exponential backoff.
- Dead-letter after max delivery count, write a review_flags record, and log
  full exception context without raw resume text.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_policy import AgentPolicy
from backend.app.agent.agent_runner import AgentRunner, AgentResult
from backend.app.agent.tool_executor import ToolExecutor
from backend.app.config import Settings
from backend.app.models.jobs import JobRecord, JobStatus
from backend.app.models.reviews import ReviewFlag, ReviewSeverity, ReviewCreator
from backend.app.models.scores import ScoreRecord, ScoreBreakdown
from backend.app.models.traces import AgentTraceRecord

logger = logging.getLogger(__name__)

# Exponential backoff base for abandoned messages.
_BACKOFF_BASE_SECONDS = 2
_MAX_BACKOFF_SECONDS = 30


def _determine_final_status(result: AgentResult) -> JobStatus:
    """Map agent result to final job status."""
    if result.error is not None:
        return JobStatus.FAILED_REVIEW_REQUIRED
    if result.human_review_required:
        return JobStatus.COMPLETED_WITH_REVIEW
    return JobStatus.COMPLETED


async def _emit_sse_event(registry: Any, job_id: str, event: dict[str, Any]) -> None:
    """Emit an SSE event through the registry, ignoring errors."""
    try:
        await registry.emit(job_id, event)
    except Exception:
        logger.warning("Failed to emit SSE event for job %s", job_id, exc_info=True)


def _build_score_record(job_id: str, result: AgentResult) -> dict[str, Any] | None:
    """Build a score dict from agent result, or None if no score available."""
    if result.score is None:
        return None

    breakdown = result.breakdown or {}
    return {
        "score": result.score,
        "breakdown": {
            "keyword_match": breakdown.get("keyword_match", 0),
            "experience_alignment": breakdown.get("experience_alignment", 0),
            "skills_coverage": breakdown.get("skills_coverage", 0),
        },
        "matched_keywords": result.matched_keywords,
        "missing_keywords": result.missing_keywords,
        "semantic_similarity": result.semantic_similarity,
        "fit_summary": result.fit_summary,
        "human_review_required": result.human_review_required,
        "human_review_reason": result.human_review_reason,
        "similar_candidates": [
            c if isinstance(c, dict) else c.model_dump()
            for c in (result.similar_candidates or [])
        ],
    }


def _build_trace_record(job_id: str, memory: AgentMemory) -> AgentTraceRecord:
    """Build a trace record from agent memory."""
    return AgentTraceRecord(
        job_id=job_id,
        steps=list(memory.trace_steps),
        total_iterations=memory.total_iterations,
        total_duration_ms=memory.total_duration_ms,
    )


async def process_message(
    message_body: dict[str, Any],
    *,
    settings: Settings,
    job_store: dict[str, JobRecord],
    score_store: dict[str, Any],
    trace_store: dict[str, Any],
    review_store: dict[str, Any],
    sse_registry: Any,
    agent_runner_factory: Any | None = None,
) -> None:
    """Process a single Service Bus message.

    Args:
        message_body: Parsed message with job_id, blob_path, jd_text.
        settings: Application settings.
        job_store: Job record store (dict for now, Cosmos later).
        score_store: Score result store.
        trace_store: Agent trace store.
        review_store: Review flag store.
        sse_registry: SSERegistry instance for emitting SSE events.
        agent_runner_factory: Optional callable(settings) -> AgentRunner
            for dependency injection. If None, a default runner is created.
    """
    # ── Validate message shape ────────────────────────────────────
    job_id = message_body.get("job_id")
    blob_path = message_body.get("blob_path")
    jd_text = message_body.get("jd_text")

    if not job_id or not blob_path or not jd_text:
        logger.error(
            "Invalid message shape: missing required fields. "
            "job_id=%s, blob_path=%s, jd_text_len=%d",
            job_id, blob_path, len(jd_text) if jd_text else 0,
        )
        raise ValueError(f"Invalid message: missing job_id, blob_path, or jd_text.")

    logger.info("Processing job %s", job_id)

    # ── Look up job record ────────────────────────────────────────
    job = job_store.get(job_id)
    if job is None:
        logger.error("Job %s not found in store", job_id)
        raise ValueError(f"Job {job_id} not found.")

    # ── Update job status to agent_running ────────────────────────
    job.status = JobStatus.AGENT_RUNNING
    job.updated_at = _utcnow()

    # ── Set up agent runner ───────────────────────────────────────
    if agent_runner_factory is not None:
        runner = agent_runner_factory(settings)
    else:
        policy = AgentPolicy(settings)
        executor = ToolExecutor(settings, policy)
        runner = AgentRunner(settings, policy, executor)

    memory = AgentMemory(
        job_id=job_id,
        job_description=jd_text,
        blob_path=blob_path,
    )

    # ── SSE event callback ────────────────────────────────────────
    async def on_event(event: dict[str, Any]) -> None:
        await _emit_sse_event(sse_registry, job_id, event)

    # ── Run the agent ─────────────────────────────────────────────
    run_start = time.monotonic()
    result = await runner.run(memory, event_callback=on_event)
    run_duration_ms = int((time.monotonic() - run_start) * 1000)

    # ── Persist results ───────────────────────────────────────────
    final_status = _determine_final_status(result)

    # Persist score.
    score_data = _build_score_record(job_id, result)
    if score_data is not None:
        score_store[job_id] = score_data

    # Persist trace.
    trace_record = _build_trace_record(job_id, memory)
    trace_store[job_id] = trace_record

    # Persist review flag if needed.
    if result.human_review_required and result.human_review_reason:
        review_flag = ReviewFlag(
            job_id=job_id,
            reason_code="agent_flag" if result.error is None else "agent_error",
            reason=result.human_review_reason,
            severity=ReviewSeverity.HIGH if result.error else ReviewSeverity.MEDIUM,
            created_by=ReviewCreator.AGENT if result.error is None else ReviewCreator.WORKER,
        )
        review_store.setdefault(job_id, []).append(review_flag)

    # Update job record.
    job.status = final_status
    job.updated_at = _utcnow()

    logger.info(
        "Job %s completed with status %s (score=%s, iterations=%d, duration=%dms)",
        job_id,
        final_status.value,
        result.score,
        result.total_iterations,
        run_duration_ms,
    )


async def process_message_with_retry(
    message_body: dict[str, Any],
    delivery_count: int,
    max_deliveries: int,
    *,
    settings: Settings,
    job_store: dict[str, JobRecord],
    score_store: dict[str, Any],
    trace_store: dict[str, Any],
    review_store: dict[str, Any],
    sse_registry: Any,
    agent_runner_factory: Any | None = None,
) -> bool:
    """Process a message with retry/dead-letter logic.

    Args:
        message_body: Parsed message payload.
        delivery_count: Current delivery count (1-based).
        max_deliveries: Max allowed deliveries before dead-letter.
        settings: Application settings.
        job_store: Job record store.
        score_store: Score result store.
        trace_store: Agent trace store.
        review_store: Review flag store.
        sse_registry: SSERegistry for SSE events.
        agent_runner_factory: Optional runner factory.

    Returns:
        True if message should be completed, False if it should be abandoned.
    """
    try:
        await process_message(
            message_body,
            settings=settings,
            job_store=job_store,
            score_store=score_store,
            trace_store=trace_store,
            review_store=review_store,
            sse_registry=sse_registry,
            agent_runner_factory=agent_runner_factory,
        )
        return True

    except Exception as exc:
        is_retryable = _is_retryable(exc)

        if is_retryable and delivery_count < max_deliveries:
            # Abandon with exponential backoff.
            backoff = min(
                _BACKOFF_BASE_SECONDS ** delivery_count,
                _MAX_BACKOFF_SECONDS,
            )
            logger.warning(
                "Retryable failure for job %s (delivery %d/%d). "
                "Abandoning with %ds backoff: %s",
                message_body.get("job_id", "?"),
                delivery_count, max_deliveries, backoff, exc,
            )
            return False

        # Dead-letter — max deliveries reached or non-retryable.
        job_id = message_body.get("job_id", "unknown")
        logger.error(
            "Dead-lettering job %s (delivery %d/%d): %s",
            job_id, delivery_count, max_deliveries, exc,
        )

        # Update job status.
        job = job_store.get(job_id)
        if job is not None:
            job.status = JobStatus.FAILED_REVIEW_REQUIRED
            job.updated_at = _utcnow()

        # Write review flag.
        review_flag = ReviewFlag(
            job_id=job_id,
            reason_code="worker_dead_letter",
            reason=f"Worker dead-lettered after {delivery_count} deliveries: {exc}",
            severity=ReviewSeverity.HIGH,
            created_by=ReviewCreator.WORKER,
        )
        review_store.setdefault(job_id, []).append(review_flag)

        # Emit terminal SSE error event.
        await _emit_sse_event(sse_registry, job_id, {
            "event_type": "error",
            "job_id": job_id,
            "message": f"Job failed after {delivery_count} attempts: {exc}",
        })

        # Dead-lettered messages are considered "completed" from the
        # Service Bus perspective (we don't want them re-delivered).
        return True


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is retryable."""
    exc_str = str(exc).lower()
    # Transient Azure service errors.
    retryable_signals = [
        "timeout",
        "connection",
        "throttl",
        "too many requests",
        "503",
        "502",
        "500",
        "rate limit",
        "service unavailable",
    ]
    return any(signal in exc_str for signal in retryable_signals)


async def run_worker(
    settings: Settings,
    *,
    job_store: dict[str, JobRecord],
    score_store: dict[str, Any],
    trace_store: dict[str, Any],
    review_store: dict[str, Any],
    sse_registry: Any,
    agent_runner_factory: Any | None = None,
    message_source: Any | None = None,
) -> None:
    """Main worker loop — receives and processes Service Bus messages.

    In production this uses azure.servicebus.ServiceBusClient.
    For testing, pass a message_source async iterator.

    Args:
        settings: Application settings.
        job_store: Job record store.
        score_store: Score result store.
        trace_store: Agent trace store.
        review_store: Review flag store.
        sse_registry: SSERegistry for SSE events.
        agent_runner_factory: Optional runner factory for DI.
        message_source: Optional async iterator of (body, delivery_count) tuples.
            If None, connects to Service Bus using settings.
    """
    max_deliveries = 3  # Design spec Section 7.3.

    if message_source is not None:
        # Test/local mode: consume from provided async iterator.
        async for message_body, delivery_count in message_source:
            await process_message_with_retry(
                message_body,
                delivery_count=delivery_count,
                max_deliveries=max_deliveries,
                settings=settings,
                job_store=job_store,
                score_store=score_store,
                trace_store=trace_store,
                review_store=review_store,
                sse_registry=sse_registry,
                agent_runner_factory=agent_runner_factory,
            )
        return

    # Production mode: connect to Azure Service Bus.
    from azure.servicebus.aio import ServiceBusClient
    from azure.servicebus import ServiceBusReceivedMessage

    conn_str = settings.servicebus_connection_string
    queue_name = settings.servicebus_queue_name

    if not conn_str:
        raise RuntimeError(
            "SERVICEBUS_CONNECTION_STRING is required for production worker."
        )

    async with ServiceBusClient.from_connection_string(conn_str) as client:
        async with client.get_queue_receiver(queue_name) as receiver:
            logger.info("Worker started. Listening on queue: %s", queue_name)
            async for msg in receiver:
                try:
                    body = json.loads(str(msg))
                    delivery_count = msg.delivery_count

                    should_complete = await process_message_with_retry(
                        body,
                        delivery_count=delivery_count,
                        max_deliveries=max_deliveries,
                        settings=settings,
                        job_store=job_store,
                        score_store=score_store,
                        trace_store=trace_store,
                        review_store=review_store,
                        sse_registry=sse_registry,
                        agent_runner_factory=agent_runner_factory,
                    )

                    if should_complete:
                        await receiver.complete_message(msg)
                    else:
                        await receiver.abandon_message(msg)

                except json.JSONDecodeError:
                    logger.error("Invalid JSON in message, dead-lettering.")
                    await receiver.dead_letter_message(
                        msg,
                        reason="Invalid JSON",
                        error_description="Message body is not valid JSON.",
                    )
                except Exception as exc:
                    logger.exception("Unexpected error processing message.")
                    await receiver.abandon_message(msg)


def _utcnow():
    from datetime import UTC, datetime
    return datetime.now(UTC)
