"""Review flag model — Cosmos DB `review_flags` container.

Design spec Section 7.1: partition key /job_id, TTL 90 days.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.app.models.jobs import _gen_id, _utcnow


class ReviewSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewCreator(str, Enum):
    AGENT = "agent"
    POLICY_GUARDRAIL = "policy_guardrail"
    WORKER = "worker"


class ReviewFlag(BaseModel):
    id: str = Field(default_factory=_gen_id)
    job_id: str
    reason_code: str
    reason: str
    severity: ReviewSeverity = ReviewSeverity.MEDIUM
    created_at: datetime = Field(default_factory=_utcnow)
    created_by: ReviewCreator = ReviewCreator.AGENT
