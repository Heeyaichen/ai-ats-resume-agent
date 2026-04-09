"""Tool executor — dispatches validated tool calls to service adapters.

Design spec Section 4.4: dispatches validated tool calls to service
adapters and normalizes failures.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Awaitable

from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_policy import AgentPolicy
from backend.app.config import Settings
from backend.app.models.traces import TraceStep

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool call fails after all retries."""

    def __init__(self, tool_name: str, message: str, retryable: bool = False) -> None:
        self.tool_name = tool_name
        self.message = message
        self.retryable = retryable
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ToolExecutor:
    """Dispatches tool calls to service adapters with retry logic.

    Each tool call is validated by the policy, dispatched to the
    appropriate adapter, and the result is validated and stored in memory.
    """

    def __init__(
        self,
        settings: Settings,
        policy: AgentPolicy,
        adapters: dict[str, Any] | None = None,
    ) -> None:
        self._settings = settings
        self._policy = policy
        self._max_retries = settings.agent_max_retries_per_tool
        # Adapter registry: tool_name -> adapter instance
        self._adapters: dict[str, Any] = adapters or {}

    def register_adapter(self, tool_name: str, adapter: Any) -> None:
        """Register a service adapter for a tool name."""
        self._adapters[tool_name] = adapter

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        memory: AgentMemory,
        *,
        event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """Execute a tool call with policy check and retries.

        Args:
            tool_name: Canonical tool name.
            arguments: Raw arguments from the model's function call.
            memory: Current agent memory.
            event_callback: Optional async callback for SSE events.

        Returns:
            The validated tool result as a dict.

        Raises:
            ToolExecutionError: If the tool fails after max retries.
            ValueError: If the policy blocks the call.
        """
        # Policy check.
        decision = self._policy.check_tool_call(tool_name, memory)
        if not decision.allowed:
            if decision.force_flag:
                memory.human_review_flagged = True
                memory.human_review_reasons.append(decision.flag_reason)
            raise ValueError(decision.reason)

        adapter = self._adapters.get(tool_name)
        if adapter is None:
            raise ToolExecutionError(
                tool_name, f"No adapter registered for tool '{tool_name}'.",
                retryable=False,
            )

        # Execute with retry loop.
        last_error: Exception | None = None
        for attempt in range(1 + self._max_retries):
            start = time.monotonic()

            try:
                result = await adapter(arguments, memory)
                duration_ms = int((time.monotonic() - start) * 1000)

                # Store result in memory.
                memory.record_tool_result(tool_name, result)

                # Build sanitized trace step.
                summary = _sanitize_result_summary(tool_name, result)
                step = TraceStep(
                    iteration=memory.total_iterations + 1,
                    tool_name=tool_name,
                    arguments_summary=_sanitize_arguments(tool_name, arguments),
                    result_summary=summary,
                    duration_ms=duration_ms,
                )
                memory.add_trace_step(step)

                # Emit SSE event if callback provided.
                if event_callback is not None:
                    from backend.app.models.events import ToolResultEvent
                    event = ToolResultEvent(
                        job_id=memory.job_id,
                        iteration=step.iteration,
                        tool_name=tool_name,
                        result_summary=summary,
                        duration_ms=duration_ms,
                    )
                    await event_callback(event.model_dump(mode="json"))

                logger.info(
                    "Tool %s completed in %dms (attempt %d)",
                    tool_name, duration_ms, attempt + 1,
                )
                return result

            except Exception as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                last_error = exc
                retry_count = memory.increment_retry(tool_name)
                logger.warning(
                    "Tool %s failed (attempt %d, retry %d/%d): %s",
                    tool_name, attempt + 1, retry_count, self._max_retries, exc,
                )

        # All retries exhausted.
        raise ToolExecutionError(
            tool_name,
            f"Failed after {1 + self._max_retries} attempts: {last_error}",
            retryable=False,
        )


def _sanitize_arguments(tool_name: str, arguments: dict[str, Any]) -> str:
    """Create a human-readable but PII-safe summary of tool arguments."""
    if tool_name == "extract_resume_text":
        return f"blob_path={arguments.get('blob_path', '?')}"
    if tool_name in ("score_resume", "compute_semantic_similarity"):
        return f"JD length={len(arguments.get('job_description', ''))}, resume length={len(arguments.get('resume_text', ''))}"
    if tool_name == "flag_for_human_review":
        return f"reason={arguments.get('reason', '?')[:60]}"
    if tool_name == "generate_fit_summary":
        return f"score={arguments.get('score', '?')}, matched={len(arguments.get('matched_keywords', []))}, missing={len(arguments.get('missing_keywords', []))}"
    if tool_name == "detect_language":
        return f"text length={len(arguments.get('text', ''))}"
    if tool_name == "translate_text":
        return f"source={arguments.get('source_language', '?')}, text length={len(arguments.get('text', ''))}"
    if tool_name == "check_pii_and_safety":
        return f"text length={len(arguments.get('text', ''))}"
    if tool_name == "search_similar_candidates":
        return f"ref={arguments.get('resume_embedding_ref', '?')}, top_k={arguments.get('top_k', 3)}"
    return json.dumps(arguments, default=str)[:100]


def _sanitize_result_summary(tool_name: str, result: dict[str, Any]) -> str:
    """Create a PII-safe summary of a tool result."""
    if tool_name == "extract_resume_text":
        return f"Extracted {result.get('page_count', '?')} pages with {result.get('confidence', 0):.2f} confidence."
    if tool_name == "detect_language":
        return f"Detected {result.get('language_name', '?')} ({result.get('language_code', '?')}) with {result.get('confidence', 0):.2f} confidence."
    if tool_name == "translate_text":
        return f"Translated from {result.get('source_language', '?')} to en ({len(result.get('translated_text', ''))} chars)."
    if tool_name == "check_pii_and_safety":
        pii = "PII detected" if result.get("pii_detected") else "No PII"
        safety = "safety flagged" if result.get("safety_flagged") else "no safety issues"
        return f"{pii}, {safety}. Categories: {result.get('pii_categories', []) + result.get('safety_categories', [])}"
    if tool_name == "score_resume":
        return f"Score: {result.get('score', 0)}/100, confidence: {result.get('confidence', 0):.2f}. Matched: {len(result.get('matched_keywords', []))} keywords."
    if tool_name == "compute_semantic_similarity":
        return f"Similarity: {result.get('similarity_score', 0):.3f} (cache_hit={result.get('cache_hit', False)})."
    if tool_name == "search_similar_candidates":
        return f"Found {len(result.get('similar_candidates', []))} similar candidates."
    if tool_name == "flag_for_human_review":
        return f"Flagged: review_id={result.get('review_id', '?')}."
    if tool_name == "generate_fit_summary":
        return f"Summary generated ({len(result.get('summary', ''))} chars)."
    return str(result)[:100]
