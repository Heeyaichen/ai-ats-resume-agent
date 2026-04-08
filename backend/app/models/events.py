"""SSE event models — streamed to the client during agent execution.

Design spec Section 5.2: every payload includes event_type, job_id, timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.jobs import _utcnow


class AgentEventType(str, Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPLETE = "complete"
    ERROR = "error"


class _BaseEvent(BaseModel):
    """Fields present in every SSE event."""

    event_type: AgentEventType
    job_id: str
    timestamp: datetime = Field(default_factory=_utcnow)


class ToolCallEvent(_BaseEvent):
    event_type: AgentEventType = AgentEventType.TOOL_CALL
    iteration: int
    tool_name: str
    arguments_summary: str


class ToolResultEvent(_BaseEvent):
    event_type: AgentEventType = AgentEventType.TOOL_RESULT
    iteration: int
    tool_name: str
    result_summary: str
    duration_ms: int


class CompleteEvent(_BaseEvent):
    event_type: AgentEventType = AgentEventType.COMPLETE
    result: dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(_BaseEvent):
    event_type: AgentEventType = AgentEventType.ERROR
    message: str
    retryable: bool = False
