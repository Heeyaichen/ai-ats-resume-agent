"""Score router — GET /api/score/{job_id} and SSE stream.

Design spec Section 5.1:
- GET /api/score/{job_id}: return job status and score if available.
- GET /api/score/{job_id}/stream: SSE event stream.

Design spec Section 5.2:
- Valid SSE framing: data: {json}\\n\\n
- Events: tool_call, tool_result, complete, error
- 5-minute inactivity timeout
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.models.jobs import JobRecord

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory SSE event queues: job_id -> asyncio.Queue
# Production will use Redis pub/sub or similar for cross-replica support.
_sse_queues: dict[str, list[asyncio.Queue[str]]] = {}

SSE_TIMEOUT_SECONDS = 300  # 5-minute inactivity timeout per spec.


class SSERegistry:
    """Manages SSE event queues for streaming agent progress to clients."""

    @staticmethod
    def register(job_id: str) -> asyncio.Queue[str]:
        """Create and register a new SSE queue for a job."""
        q: asyncio.Queue[str] = asyncio.Queue()
        if job_id not in _sse_queues:
            _sse_queues[job_id] = []
        _sse_queues[job_id].append(q)
        return q

    @staticmethod
    async def emit(job_id: str, event: dict[str, Any]) -> None:
        """Push an event dict to all registered queues for a job."""
        payload = json.dumps(event, default=str)
        queues = _sse_queues.get(job_id, [])
        for q in queues:
            await q.put(payload)

    @staticmethod
    def unregister(job_id: str, queue: asyncio.Queue[str]) -> None:
        """Remove a queue when the client disconnects."""
        queues = _sse_queues.get(job_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            _sse_queues.pop(job_id, None)


def get_sse_registry(request: Request) -> SSERegistry:
    """Get the SSE registry from app state."""
    return request.app.state.sse_registry


@router.get("/api/score/{job_id}")
async def get_score(job_id: str, request: Request) -> dict[str, Any]:
    """Return job status and score if available.

    Design spec: 200 when job exists, 404 when not found.
    """
    job_store: dict[str, JobRecord] = request.app.state.job_store
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    response: dict[str, Any] = {
        "job_id": job.id,
        "status": job.status.value,
    }

    # Attach score if available.
    score_store: dict = request.app.state.score_store
    score = score_store.get(job_id)
    if score is not None:
        response["score"] = score

    return response


@router.get("/api/score/{job_id}/stream")
async def score_stream(job_id: str, request: Request) -> StreamingResponse:
    """SSE stream for agent progress.

    Design spec: valid SSE framing, 5-minute inactivity timeout.
    """
    # Verify job exists.
    job_store: dict[str, JobRecord] = request.app.state.job_store
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found.")

    registry = get_sse_registry(request)
    queue = registry.register(job_id)

    async def event_generator() -> Any:
        """Yield SSE events until complete/error/timeout/disconnect."""
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(
                        queue.get(), timeout=SSE_TIMEOUT_SECONDS,
                    )
                    yield f"data: {payload}\n\n"
                    # Check for terminal events.
                    event = json.loads(payload)
                    if event.get("event_type") in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event_type': 'error', 'job_id': job_id, 'message': 'Stream timed out due to inactivity.'})}\n\n"
                    break
        finally:
            registry.unregister(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering.
        },
    )
