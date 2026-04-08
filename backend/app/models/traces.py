"""Agent trace model — Cosmos DB `agent_traces` container.

Design spec Section 7.1: partition key /job_id, TTL 90 days.
contains_raw_text must always be False.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.app.models.jobs import _gen_id, _utcnow


class TraceStep(BaseModel):
    """One agent iteration: a tool call and its summarized result."""

    iteration: int
    tool_name: str
    arguments_summary: str
    result_summary: str
    duration_ms: int


class AgentTraceRecord(BaseModel):
    id: str = Field(default_factory=_gen_id)
    job_id: str
    steps: list[TraceStep] = Field(default_factory=list)
    total_iterations: int = 0
    total_duration_ms: int = 0
    contains_raw_text: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
