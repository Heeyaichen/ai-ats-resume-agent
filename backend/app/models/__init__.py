"""Domain models shared across the application.

Models here mirror the Cosmos DB schemas (design spec Section 7.1),
SSE event payloads (Section 5.2), and API request/response contracts
(Section 5.1).
"""

from backend.app.models.jobs import JobRecord, JobStatus, UploadResponse
from backend.app.models.candidates import CandidateRecord
from backend.app.models.scores import (
    ScoreBreakdown,
    ScoreRecord,
    SimilarCandidate,
)
from backend.app.models.traces import AgentTraceRecord, TraceStep
from backend.app.models.reviews import ReviewFlag, ReviewSeverity, ReviewCreator
from backend.app.models.events import (
    AgentEventType,
    ToolCallEvent,
    ToolResultEvent,
    CompleteEvent,
    ErrorEvent,
)
from backend.app.models.health import HealthResponse

__all__ = [
    "JobRecord",
    "JobStatus",
    "UploadResponse",
    "CandidateRecord",
    "ScoreBreakdown",
    "ScoreRecord",
    "SimilarCandidate",
    "AgentTraceRecord",
    "TraceStep",
    "ReviewFlag",
    "ReviewSeverity",
    "ReviewCreator",
    "AgentEventType",
    "ToolCallEvent",
    "ToolResultEvent",
    "CompleteEvent",
    "ErrorEvent",
    "HealthResponse",
]
