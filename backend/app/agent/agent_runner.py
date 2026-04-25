"""Agent runner — owns the iteration loop and final result compilation.

Design spec Section 4.4: owns the iteration loop, model calls,
guardrails, retries, max iterations, event emission, and final
result compilation.

The runner uses non-streaming OpenAI calls per spec Section 2.5.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Awaitable

from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_policy import AgentPolicy
from backend.app.agent.tool_executor import ToolExecutor, ToolExecutionError
from backend.app.agent.tool_registry import get_tool_schemas
from backend.app.config import Settings
from backend.app.models.events import (
    ToolCallEvent,
    CompleteEvent,
    ErrorEvent,
)

logger = logging.getLogger(__name__)

_AGENT_SYSTEM_PROMPT = (
    "You are an ATS resume screening agent. You have access to tools for "
    "extracting resume text, detecting language, translating, checking PII "
    "and content safety, scoring, computing semantic similarity, searching "
    "similar candidates, flagging for human review, and generating a fit "
    "summary.\n\n"
    "Your goal is to produce a complete, trustworthy ATS report for the "
    "given resume and job description.\n\n"
    "IMPORTANT RULES:\n"
    "- Always start by extracting the resume text.\n"
    "- Always check PII and safety before scoring.\n"
    "- Detect language early and translate if not English.\n"
    "- Complete scoring, semantic similarity, and fit summary before finishing.\n"
    "- Flag for human review if you encounter issues you cannot resolve.\n"
    "- Never include raw PII in your responses.\n"
)


class AgentResult:
    """Compiled result from a completed agent run."""

    def __init__(
        self,
        job_id: str,
        *,
        score: int | None = None,
        breakdown: dict[str, int] | None = None,
        matched_keywords: list[str] | None = None,
        missing_keywords: list[str] | None = None,
        semantic_similarity: float | None = None,
        fit_summary: str | None = None,
        human_review_required: bool = False,
        human_review_reason: str | None = None,
        similar_candidates: list[dict[str, Any]] | None = None,
        total_iterations: int = 0,
        total_duration_ms: int = 0,
        error: str | None = None,
    ) -> None:
        self.job_id = job_id
        self.score = score
        self.breakdown = breakdown
        self.matched_keywords = matched_keywords or []
        self.missing_keywords = missing_keywords or []
        self.semantic_similarity = semantic_similarity
        self.fit_summary = fit_summary
        self.human_review_required = human_review_required
        self.human_review_reason = human_review_reason
        self.similar_candidates = similar_candidates or []
        self.total_iterations = total_iterations
        self.total_duration_ms = total_duration_ms
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "score": self.score,
            "breakdown": self.breakdown,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "semantic_similarity": self.semantic_similarity,
            "fit_summary": self.fit_summary,
            "human_review_required": self.human_review_required,
            "human_review_reason": self.human_review_reason,
            "similar_candidates": self.similar_candidates,
            "total_iterations": self.total_iterations,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }


class AgentRunner:
    """Runs the guarded agent loop for a single job.

    Usage:
        runner = AgentRunner(settings, policy, executor)
        result = await runner.run(memory)
    """

    def __init__(
        self,
        settings: Settings,
        policy: AgentPolicy,
        executor: ToolExecutor,
        *,
        openai_client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._policy = policy
        self._executor = executor
        self._max_iterations = settings.agent_max_iterations
        self._tool_schemas = get_tool_schemas()

        if openai_client is not None:
            self._openai_client = openai_client
        else:
            from backend.app.services.openai_adapter import build_async_openai_client
            self._openai_client = build_async_openai_client(
                endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.openai_api_version,
            )

    async def run(
        self,
        memory: AgentMemory,
        *,
        event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> AgentResult:
        """Execute the agent loop until completion or error.

        Args:
            memory: Initial agent memory with job_id, blob_path, job_description.
            event_callback: Optional async callback for SSE events.

        Returns:
            Compiled AgentResult with all available data.
        """
        run_start = time.monotonic()

        try:
            # Seed the conversation with the system prompt and job context.
            memory.messages.append({
                "role": "system",
                "content": _AGENT_SYSTEM_PROMPT,
            })
            memory.messages.append({
                "role": "user",
                "content": (
                    f"Job ID: {memory.job_id}\n"
                    f"Resume blob path: {memory.blob_path}\n"
                    f"Job Description:\n{memory.job_description}\n\n"
                    "Please screen this resume against the job description."
                ),
            })

            for _ in range(self._max_iterations + 1):
                # Check iteration limit.
                iter_check = self._policy.check_iteration_limit(memory)
                if iter_check.force_complete:
                    await self._handle_flag(iter_check, memory, event_callback)
                    break

                # Call the model.
                response = await self._call_model(memory)

                # Process the response.
                choice = response.choices[0] if response.choices else None
                if choice is None:
                    logger.warning("Empty response from model")
                    break

                message = choice.message

                # If model produced tool calls, execute them.
                if hasattr(message, "tool_calls") and message.tool_calls:
                    # Add assistant message with tool calls to history.
                    memory.messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    })

                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                        # Emit tool_call event.
                        if event_callback is not None:
                            from backend.app.agent.tool_executor import _sanitize_arguments
                            call_event = ToolCallEvent(
                                job_id=memory.job_id,
                                iteration=memory.total_iterations + 1,
                                tool_name=tool_name,
                                arguments_summary=_sanitize_arguments(tool_name, arguments),
                            )
                            await event_callback(call_event.model_dump(mode="json"))

                        try:
                            result = await self._executor.execute(
                                tool_name, arguments, memory,
                                event_callback=event_callback,
                            )
                            # Add tool result to message history.
                            memory.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result, default=str),
                            })
                        except (ToolExecutionError, ValueError) as exc:
                            logger.error("Tool execution failed: %s", exc)
                            # Add error as tool result so model can react.
                            memory.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({"error": str(exc)}),
                            })

                elif choice.finish_reason == "stop":
                    # Model finished without tool calls — check if we're done.
                    # If required tools are missing but extraction succeeded,
                    # deterministically run the missing tools before finishing.
                    if not memory.all_required_complete and memory.extraction_done:
                        await self._run_missing_required_tools(memory, event_callback)

                    completion = self._policy.check_completion(memory)
                    if completion.force_flag:
                        await self._handle_flag(completion, memory, event_callback)
                    # Add assistant response to history.
                    memory.messages.append({
                        "role": "assistant",
                        "content": message.content,
                    })
                    break

                else:
                    # Some other finish reason — add to history and continue.
                    memory.messages.append({
                        "role": "assistant",
                        "content": message.content,
                    })

            # Compile final result.
            result = self._compile_result(memory)

            # Emit complete event.
            if event_callback is not None:
                complete_event = CompleteEvent(
                    job_id=memory.job_id,
                    result=result.to_dict(),
                )
                await event_callback(complete_event.model_dump(mode="json"))

            return result

        except Exception as exc:
            logger.exception("Agent run failed for job %s", memory.job_id)
            duration = int((time.monotonic() - run_start) * 1000)

            # Emit error event.
            if event_callback is not None:
                error_event = ErrorEvent(
                    job_id=memory.job_id,
                    message=str(exc),
                    retryable=False,
                )
                await event_callback(error_event.model_dump(mode="json"))

            return AgentResult(
                job_id=memory.job_id,
                human_review_required=True,
                human_review_reason=f"Agent run failed: {exc}",
                total_iterations=memory.total_iterations,
                total_duration_ms=duration,
                error=str(exc),
            )

    async def _call_model(self, memory: AgentMemory) -> Any:
        """Make a non-streaming chat completion call."""
        return await self._openai_client.chat.completions.create(
            model=self._settings.chat_model_deployment_name,
            messages=memory.messages,
            tools=self._tool_schemas,
            temperature=0.0,
        )

    async def _handle_flag(
        self,
        decision: Any,
        memory: AgentMemory,
        event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None,
    ) -> None:
        """Apply a forced flag from policy."""
        if decision.force_flag:
            memory.human_review_flagged = True
            memory.human_review_reasons.append(decision.flag_reason)

    async def _run_missing_required_tools(
        self,
        memory: AgentMemory,
        event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None,
    ) -> None:
        """Deterministically run missing required tools using memory state.

        Called when the model stops early but extraction produced usable text.
        Runs check_pii_and_safety (if not done), then score_resume,
        compute_semantic_similarity, and generate_fit_summary.
        """
        resume_text = memory.sanitized_resume_text or memory.raw_resume_text

        # Don't force scoring if extraction produced no usable text.
        if not resume_text or len(resume_text.strip()) < 20:
            return

        tool_order = ["check_pii_and_safety", "score_resume",
                       "compute_semantic_similarity", "generate_fit_summary"]

        for tool_name in tool_order:
            if tool_name in memory.completed_tools:
                continue

            # Build deterministic arguments from memory.
            args = self._build_deterministic_args(tool_name, memory)

            # Emit tool_call event.
            if event_callback is not None:
                from backend.app.agent.tool_executor import _sanitize_arguments
                call_event = ToolCallEvent(
                    job_id=memory.job_id,
                    iteration=memory.total_iterations + 1,
                    tool_name=tool_name,
                    arguments_summary=_sanitize_arguments(tool_name, args),
                )
                await event_callback(call_event.model_dump(mode="json"))

            try:
                result = await self._executor.execute(
                    tool_name, args, memory,
                    event_callback=event_callback,
                )
                memory.messages.append({
                    "role": "tool",
                    "tool_call_id": f"runtime-{tool_name}",
                    "content": json.dumps(result, default=str),
                })
            except Exception as exc:
                logger.warning(
                    "Runtime completion: tool %s failed: %s", tool_name, exc,
                )

    def _build_deterministic_args(
        self, tool_name: str, memory: AgentMemory,
    ) -> dict[str, Any]:
        """Build tool arguments from memory for deterministic execution."""
        resume_text = memory.sanitized_resume_text or memory.raw_resume_text

        if tool_name == "check_pii_and_safety":
            return {"text": resume_text}
        if tool_name == "score_resume":
            return {
                "resume_text": resume_text,
                "job_description": memory.job_description,
            }
        if tool_name == "compute_semantic_similarity":
            return {
                "resume_text": resume_text,
                "job_description": memory.job_description,
            }
        if tool_name == "generate_fit_summary":
            score_data = memory.get_score_result() or {}
            return {
                "resume_text": resume_text,
                "job_description": memory.job_description,
                "score": score_data.get("score", 0),
                "matched_keywords": score_data.get("matched_keywords", []),
                "missing_keywords": score_data.get("missing_keywords", []),
            }
        return {}

    def _compile_result(self, memory: AgentMemory) -> AgentResult:
        """Build the final AgentResult from memory state."""
        score_data = memory.get_score_result()
        similarity_data = memory.get_similarity_result()
        summary_data = memory.completed_tools.get("generate_fit_summary")
        search_data = memory.completed_tools.get("search_similar_candidates")

        score: int | None = None
        breakdown: dict[str, int] | None = None
        matched_keywords: list[str] | None = None
        missing_keywords: list[str] | None = None

        if score_data:
            score = score_data.get("score")
            bd = score_data.get("breakdown", {})
            breakdown = {
                "keyword_match": bd.get("keyword_match", 0),
                "experience_alignment": bd.get("experience_alignment", 0),
                "skills_coverage": bd.get("skills_coverage", 0),
            }
            matched_keywords = score_data.get("matched_keywords", [])
            missing_keywords = score_data.get("missing_keywords", [])

        semantic_similarity: float | None = None
        if similarity_data:
            semantic_similarity = similarity_data.get("similarity_score")

        fit_summary: str | None = None
        if summary_data:
            fit_summary = summary_data.get("summary")

        similar_candidates: list[dict[str, Any]] | None = None
        if search_data:
            similar_candidates = search_data.get("similar_candidates", [])

        human_review_reason: str | None = None
        if memory.human_review_reasons:
            human_review_reason = "; ".join(memory.human_review_reasons)

        return AgentResult(
            job_id=memory.job_id,
            score=score,
            breakdown=breakdown,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            semantic_similarity=semantic_similarity,
            fit_summary=fit_summary,
            human_review_required=memory.human_review_flagged,
            human_review_reason=human_review_reason,
            similar_candidates=similar_candidates,
            total_iterations=memory.total_iterations,
            total_duration_ms=memory.total_duration_ms,
        )
