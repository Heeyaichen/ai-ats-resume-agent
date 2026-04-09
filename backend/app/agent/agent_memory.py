"""Agent memory — stores model messages, milestones, and tool history.

Design spec Section 4.4: stores model messages, accepted tool calls,
accepted tool results, milestones, and sanitized trace summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.models.traces import TraceStep


@dataclass
class AgentMemory:
    """Mutable state for a single agent run.

    The runner updates this after each iteration. The policy reads it
    to decide what must happen next.
    """

    job_id: str
    job_description: str = ""
    blob_path: str = ""

    # Accumulated OpenAI chat messages (system + user + assistant + tool).
    messages: list[dict[str, Any]] = field(default_factory=list)

    # Tool results keyed by tool name for milestone tracking.
    # Value is the parsed tool output dict.
    completed_tools: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Per-tool retry counts.
    retry_counts: dict[str, int] = field(default_factory=dict)

    # Sanitized trace steps for persistence.
    trace_steps: list[TraceStep] = field(default_factory=list)

    # Running totals.
    total_iterations: int = 0
    total_duration_ms: int = 0

    # Resume text state (held in process memory only — never persisted).
    raw_resume_text: str = ""
    sanitized_resume_text: str = ""
    resume_embedding: list[float] = field(default_factory=list)

    # Human review tracking.
    human_review_flagged: bool = False
    human_review_reasons: list[str] = field(default_factory=list)

    # ── Milestone queries ────────────────────────────────────────

    @property
    def extraction_done(self) -> bool:
        return "extract_resume_text" in self.completed_tools

    @property
    def pii_safety_done(self) -> bool:
        return "check_pii_and_safety" in self.completed_tools

    @property
    def language_detected(self) -> bool:
        return "detect_language" in self.completed_tools

    @property
    def translation_done(self) -> bool:
        return "translate_text" in self.completed_tools

    @property
    def scoring_done(self) -> bool:
        return "score_resume" in self.completed_tools

    @property
    def similarity_done(self) -> bool:
        return "compute_semantic_similarity" in self.completed_tools

    @property
    def summary_done(self) -> bool:
        return "generate_fit_summary" in self.completed_tools

    @property
    def all_required_complete(self) -> bool:
        """The three tools that must all complete before a report is done."""
        return self.scoring_done and self.similarity_done and self.summary_done

    # ── Mutation helpers ─────────────────────────────────────────

    def record_tool_result(self, tool_name: str, result: dict[str, Any]) -> None:
        """Store a completed tool result and update state."""
        self.completed_tools[tool_name] = result

        # Extract resume text into process memory.
        if tool_name == "extract_resume_text":
            self.raw_resume_text = result.get("text", "")

        # Store sanitized text after PII check.
        if tool_name == "check_pii_and_safety":
            self.sanitized_resume_text = result.get("sanitized_text", "")

        # Track human review flags.
        if tool_name == "flag_for_human_review":
            self.human_review_flagged = True

    def increment_retry(self, tool_name: str) -> int:
        """Increment and return the retry count for a tool."""
        self.retry_counts[tool_name] = self.retry_counts.get(tool_name, 0) + 1
        return self.retry_counts[tool_name]

    def add_trace_step(self, step: TraceStep) -> None:
        """Append a sanitized trace step."""
        self.trace_steps.append(step)
        self.total_iterations += 1
        self.total_duration_ms += step.duration_ms

    def get_language_code(self) -> str | None:
        """Return detected language code, or None if not detected yet."""
        result = self.completed_tools.get("detect_language")
        if result:
            return result.get("language_code")
        return None

    def get_score_result(self) -> dict[str, Any] | None:
        """Return the score result dict, or None."""
        return self.completed_tools.get("score_resume")

    def get_similarity_result(self) -> dict[str, Any] | None:
        """Return the similarity result dict, or None."""
        return self.completed_tools.get("compute_semantic_similarity")
