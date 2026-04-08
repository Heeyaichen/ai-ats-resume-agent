"""Job record model — Cosmos DB `jobs` container.

Design spec Section 7.1: partition key /id, TTL 90 days.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _gen_id() -> str:
    return __import__("uuid").uuid4().hex


class JobStatus(str, Enum):
    QUEUED = "queued"
    AGENT_RUNNING = "agent_running"
    COMPLETED = "completed"
    COMPLETED_WITH_REVIEW = "completed_with_review"
    FAILED_REVIEW_REQUIRED = "failed_review_required"
    ERROR = "error"


class JobRecord(BaseModel):
    """Persisted job document."""

    id: str = Field(default_factory=_gen_id)
    status: JobStatus = JobStatus.QUEUED
    filename: str
    blob_path: str
    job_description: str
    uploaded_by: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    retention_hold: bool = False


class UploadResponse(BaseModel):
    """Returned by POST /api/upload."""

    job_id: str
    status: JobStatus = JobStatus.QUEUED
