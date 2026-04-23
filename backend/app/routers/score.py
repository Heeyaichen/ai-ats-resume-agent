"""Score router — GET /api/score/{job_id} and SSE stream.

Design spec Section 5.1:
- GET /api/score/{job_id}: return job status and score if available.
- GET /api/score/{job_id}/stream: SSE event stream.

Design spec Section 5.2:
- Valid SSE framing: data: {json}\n\n
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

SSE_TIMEOUT_SECONDS = 300  # 5-minute inactivity timeout per spec.

# Redis channel prefix for SSE events.
_SSE_CHANNEL_PREFIX = "sse:"


class SSERegistry:
    """Manages SSE event delivery using Redis pub/sub for cross-process support.

    Falls back to in-process asyncio queues when redis_url is not configured.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url
        self._redis: Any | None = None
        # In-process fallback.
        self._local_queues: dict[str, list[asyncio.Queue[str]]] = {}

    async def _get_redis(self) -> Any:
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)
        return self._redis

    async def emit(self, job_id: str, event: dict[str, Any]) -> None:
        """Push an event to the Redis channel and local queues."""
        payload = json.dumps(event, default=str)
        # Deliver to local in-process queues.
        for q in self._local_queues.get(job_id, []):
            await q.put(payload)
        # Publish to Redis for cross-process delivery.
        try:
            r = await self._get_redis()
            if r is not None:
                await r.publish(f"{_SSE_CHANNEL_PREFIX}{job_id}", payload)
        except Exception:
            logger.warning(
                "Failed to publish SSE event to Redis for job %s",
                job_id, exc_info=True,
            )

    def register(self, job_id: str) -> asyncio.Queue[str]:
        """Create and register a new local SSE queue for a job."""
        q: asyncio.Queue[str] = asyncio.Queue()
        if job_id not in self._local_queues:
            self._local_queues[job_id] = []
        self._local_queues[job_id].append(q)
        return q

    def unregister(self, job_id: str, queue: asyncio.Queue[str]) -> None:
        """Remove a queue when the client disconnects."""
        queues = self._local_queues.get(job_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._local_queues.pop(job_id, None)

    async def subscribe(
        self, job_id: str, queue: asyncio.Queue[str],
    ) -> tuple[Any, asyncio.Task] | None:
        """Subscribe to Redis channel and forward events to the queue.

        Returns (pubsub, forward_task) or None if Redis is unavailable.
        """
        r = await self._get_redis()
        if r is None:
            return None
        pubsub = r.pubsub()
        await pubsub.subscribe(f"{_SSE_CHANNEL_PREFIX}{job_id}")

        async def _forward() -> None:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    await queue.put(
                        data.decode() if isinstance(data, bytes) else data,
                    )

        task = asyncio.create_task(_forward())
        return pubsub, task


def get_sse_registry(request: Request) -> SSERegistry:
    """Get the SSE registry from app state."""
    return request.app.state.sse_registry


@router.get("/api/score/{job_id}")
async def get_score(job_id: str, request: Request) -> dict[str, Any]:
    """Return job status and score if available.

    Design spec: 200 when job exists, 404 when not found.
    """
    cosmos = getattr(request.app.state, "cosmos_adapter", None)

    if cosmos is not None:
        job = await cosmos.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        response: dict[str, Any] = {
            "job_id": job.id,
            "status": job.status.value,
        }
        # Try in-memory score first, then Cosmos.
        score = getattr(request.app.state, "score_store", {}).get(job_id)
        if score is None:
            try:
                container = await cosmos._get_container("scores")
                # Query scores by job_id (partition key).
                items = container.query_items(
                    query="SELECT * FROM c WHERE c.job_id = @jid",
                    parameters=[{"name": "@jid", "value": job_id}],
                    partition_key=job_id,
                )
                async for item in items:
                    score = {k: v for k, v in item.items() if not k.startswith("_")}
                    break
            except Exception:
                pass
        if score is not None:
            response["score"] = score
        return response

    # Fallback: in-memory store.
    job_store: dict[str, JobRecord] = request.app.state.job_store
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    response = {
        "job_id": job.id,
        "status": job.status.value,
    }
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
    cosmos = getattr(request.app.state, "cosmos_adapter", None)

    # Verify job exists.
    if cosmos is not None:
        job = await cosmos.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
    else:
        job_store: dict[str, JobRecord] = request.app.state.job_store
        if job_id not in job_store:
            raise HTTPException(status_code=404, detail="Job not found.")

    registry = get_sse_registry(request)
    queue = registry.register(job_id)

    # Subscribe to Redis pub/sub for cross-process events.
    sub_result = await registry.subscribe(job_id, queue)
    pubsub_cleanup = None
    if sub_result is not None:
        pubsub, forward_task = sub_result

        async def _cleanup() -> None:
            forward_task.cancel()
            await pubsub.unsubscribe(f"{_SSE_CHANNEL_PREFIX}{job_id}")
            await pubsub.close()

        pubsub_cleanup = _cleanup

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
            if pubsub_cleanup is not None:
                try:
                    await pubsub_cleanup()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
