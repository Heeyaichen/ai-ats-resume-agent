"""Azure Cosmos DB adapter — job records, scores, traces, review flags.

Design spec Section 7.1: database `ats-db` with 5 containers.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.jobs import JobRecord
from backend.app.models.scores import ScoreRecord
from backend.app.models.traces import AgentTraceRecord
from backend.app.models.reviews import ReviewFlag
from backend.app.models.tools import FlagForHumanReviewInput, FlagForHumanReviewOutput

logger = logging.getLogger(__name__)


class CosmosAdapter:
    """Wraps Azure Cosmos DB NoSQL for job, score, trace, and review data."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.cosmos_endpoint
        self._key = settings.cosmos_key
        self._database_name = settings.cosmos_database_name
        self._client: Any | None = None

    async def get_job(self, job_id: str, *, client: Any | None = None) -> JobRecord | None:
        """Read a job record by id."""
        container = await self._get_container("jobs", client)
        try:
            doc = await container.read_item(item=job_id, partition_key=job_id)
            return JobRecord(**doc)
        except Exception:
            return None

    async def upsert_job(self, job: JobRecord, *, client: Any | None = None) -> None:
        """Create or update a job record."""
        container = await self._get_container("jobs", client)
        await container.upsert_item(body=job.model_dump(mode="json"))
        logger.info("Upserted job %s (status=%s)", job.id, job.status)

    async def upsert_score(self, score: ScoreRecord, *, client: Any | None = None) -> None:
        """Create or update a score record."""
        container = await self._get_container("scores", client)
        await container.upsert_item(body=score.model_dump(mode="json"))
        logger.info("Upserted score for job %s (score=%d)", score.job_id, score.score)

    async def upsert_trace(self, trace: AgentTraceRecord, *, client: Any | None = None) -> None:
        """Create or update an agent trace record."""
        container = await self._get_container("agent_traces", client)
        await container.upsert_item(body=trace.model_dump(mode="json"))
        logger.info("Upserted trace for job %s (%d steps)", trace.job_id, len(trace.steps))

    async def flag_for_human_review(
        self,
        input_data: FlagForHumanReviewInput,
        *,
        client: Any | None = None,
    ) -> FlagForHumanReviewOutput:
        """Write a review flag. Idempotent by {job_id, reason_code}."""
        container = await self._get_container("review_flags", client)
        flag = ReviewFlag(
            job_id=input_data.job_id,
            reason_code=input_data.reason[:60],
            reason=input_data.reason,
            severity=input_data.severity,
        )
        await container.upsert_item(body=flag.model_dump(mode="json"))
        logger.info("Flagged job %s for human review: %s", input_data.job_id, input_data.reason)
        return FlagForHumanReviewOutput(review_id=flag.id, flagged=True)

    async def _get_container(self, container_name: str, client: Any | None = None) -> Any:
        if client is not None:
            # Test context: client is already a container mock.
            return client
        cosmos_client = await self._get_client()
        db = cosmos_client.get_database_client(self._database_name)
        return db.get_container_client(container_name)

    async def _get_client(self) -> Any:
        if self._client is None:
            from azure.cosmos.aio import CosmosClient

            self._client = CosmosClient(url=self._endpoint, credential=self._key)
        return self._client
