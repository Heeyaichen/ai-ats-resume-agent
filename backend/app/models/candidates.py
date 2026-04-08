"""Candidate record model — Cosmos DB `candidates` container.

Design spec Section 7.1: partition key /id, TTL 90 days.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.app.models.jobs import _gen_id, _utcnow


class CandidateRecord(BaseModel):
    id: str = Field(default_factory=_gen_id)
    job_id: str
    resume_blob_path: str
    language_detected: str | None = None
    translated: bool = False
    pii_detected: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
