"""Score record model — Cosmos DB `scores` container.

Design spec Section 7.1: partition key /job_id, TTL 90 days.
Score breakdown weights: 40 keyword, 30 experience, 30 skills (Section 4.3).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.jobs import _gen_id, _utcnow


class ScoreBreakdown(BaseModel):
    keyword_match: int = Field(ge=0, le=40)
    experience_alignment: int = Field(ge=0, le=30)
    skills_coverage: int = Field(ge=0, le=30)


class SimilarCandidate(BaseModel):
    candidate_id: str
    job_id: str
    score: int
    similarity: float


class ScoreRecord(BaseModel):
    id: str = Field(default_factory=_gen_id)
    job_id: str
    score: int = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    semantic_similarity: float | None = None
    fit_summary: str | None = None
    human_review_required: bool = False
    human_review_reason: str | None = None
    similar_candidates: list[SimilarCandidate] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
