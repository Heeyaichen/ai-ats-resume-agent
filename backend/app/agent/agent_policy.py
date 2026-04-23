"""Agent policy — enforces guardrail invariants at runtime.

Design spec Section 4.1: the runtime enforces safety and completeness
invariants. The model does NOT decide these.

Guardrails enforced:
- extract_resume_text must complete before tools needing resume text.
- check_pii_and_safety must complete before scoring/embedding/summary.
- Non-English resumes require translate_text or human review.
- score_resume, compute_semantic_similarity, generate_fit_summary must all complete.
- Auto-flag for human review on: score < 30, confidence < 0.6,
  safety flagged, extraction confidence low, max iterations, missing fields.
- Max 12 iterations, max 2 retries per tool.
"""

from __future__ import annotations

import logging

from backend.app.agent.agent_memory import AgentMemory
from backend.app.config import Settings

logger = logging.getLogger(__name__)


class PolicyDecision:
    """Result of a policy check."""

    def __init__(
        self,
        allowed: bool = True,
        *,
        reason: str = "",
        force_flag: bool = False,
        flag_reason: str = "",
        flag_severity: str = "medium",
        force_complete: bool = False,
    ) -> None:
        self.allowed = allowed
        self.reason = reason
        self.force_flag = force_flag
        self.flag_reason = flag_reason
        self.flag_severity = flag_severity
        self.force_complete = force_complete

    def __repr__(self) -> str:
        parts = [f"allowed={self.allowed}"]
        if self.reason:
            parts.append(f"reason='{self.reason}'")
        if self.force_flag:
            parts.append(f"force_flag='{self.flag_reason}'")
        if self.force_complete:
            parts.append("force_complete=True")
        return f"PolicyDecision({', '.join(parts)})"


class AgentPolicy:
    """Stateless policy checker. Each call receives the current memory."""

    def __init__(self, settings: Settings) -> None:
        self._max_iterations = settings.agent_max_iterations
        self._max_retries = settings.agent_max_retries_per_tool

    def check_tool_call(
        self,
        tool_name: str,
        memory: AgentMemory,
    ) -> PolicyDecision:
        """Check whether a tool call is allowed given current state.

        Returns a PolicyDecision with allowed=True/False and optional
        flag/complete directives.
        """
        # ── Obsolete tool rejection ────────────────────────────────
        if tool_name in ("get_embedding", "search_similar_jds"):
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' is obsolete. "
                       f"Use '{'compute_semantic_similarity' if tool_name == 'get_embedding' else 'search_similar_candidates'}'.",
            )

        # ── Retry limit ────────────────────────────────────────────
        retries = memory.retry_counts.get(tool_name, 0)
        if retries >= self._max_retries:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' exceeded max retries ({self._max_retries}).",
                force_flag=True,
                flag_reason=f"Tool '{tool_name}' failed after {self._max_retries} retries.",
                flag_severity="high",
            )

        # ── Tool-specific ordering constraints ─────────────────────

        # Tools needing resume text require extraction first.
        text_requiring_tools = {
            "detect_language",
            "check_pii_and_safety",
            "score_resume",
            "compute_semantic_similarity",
            "generate_fit_summary",
        }
        if tool_name in text_requiring_tools and not memory.extraction_done:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' requires extract_resume_text to complete first.",
            )

        # Scoring/embedding/summary require PII/safety first.
        post_pii_tools = {
            "score_resume",
            "compute_semantic_similarity",
            "generate_fit_summary",
        }
        if tool_name in post_pii_tools and not memory.pii_safety_done:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' requires check_pii_and_safety to complete first.",
            )

        return PolicyDecision(allowed=True)

    def check_iteration_limit(self, memory: AgentMemory) -> PolicyDecision:
        """Check whether the agent has exceeded the iteration limit."""
        if memory.total_iterations >= self._max_iterations:
            return PolicyDecision(
                allowed=False,
                reason=f"Max iterations ({self._max_iterations}) reached.",
                force_flag=True,
                flag_reason=f"Agent reached max iterations ({self._max_iterations}).",
                flag_severity="high",
                force_complete=True,
            )
        return PolicyDecision(allowed=True)

    def check_completion(self, memory: AgentMemory) -> PolicyDecision:
        """Check if the agent can mark the job as complete.

        Returns force_complete=True if the agent should stop and finalize
        with whatever data is available.
        """
        reasons_to_flag: list[str] = []

        # All three required tools must be done.
        if not memory.all_required_complete:
            missing = []
            if not memory.scoring_done:
                missing.append("score_resume")
            if not memory.similarity_done:
                missing.append("compute_semantic_similarity")
            if not memory.summary_done:
                missing.append("generate_fit_summary")
            reasons_to_flag.append(
                f"Missing required tools: {', '.join(missing)}."
            )

        # Non-English without translation or flag.
        lang_code = memory.get_language_code()
        if (
            lang_code is not None
            and lang_code != "en"
            and not memory.translation_done
            and not memory.human_review_flagged
        ):
            reasons_to_flag.append(
                f"Non-English language ({lang_code}) without translation or review flag."
            )

        # Score-based flags.
        score_result = memory.get_score_result()
        if score_result is not None:
            score = score_result.get("score", 100)
            confidence = score_result.get("confidence", 1.0)

            if score < 30:
                reasons_to_flag.append(f"Low score ({score}).")
            if confidence < 0.6:
                reasons_to_flag.append(f"Low confidence ({confidence:.2f}).")

        # Safety flag.
        pii_result = memory.completed_tools.get("check_pii_and_safety")
        if pii_result and pii_result.get("safety_flagged"):
            reasons_to_flag.append("Content safety flagged.")

        # Extraction confidence.
        extraction_result = memory.completed_tools.get("extract_resume_text")
        if extraction_result and extraction_result.get("confidence", 1.0) < 0.5:
            reasons_to_flag.append("Low extraction confidence.")

        if reasons_to_flag:
            flag_reason = " ".join(reasons_to_flag)
            return PolicyDecision(
                allowed=True,
                force_flag=True,
                flag_reason=flag_reason,
                flag_severity="high" if any("safety" in r.lower() for r in reasons_to_flag) else "medium",
            )

        return PolicyDecision(allowed=True)

    def should_force_early_flag(self, memory: AgentMemory) -> PolicyDecision:
        """Check if the model is trying to finish early without required tools."""
        # If the model produced a finish_reason of "stop" but required tools
        # are incomplete, force a flag.
        if not memory.extraction_done:
            return PolicyDecision(
                force_flag=True,
                flag_reason="Model attempted to finish without extracting resume text.",
                flag_severity="high",
                force_complete=True,
            )
        return PolicyDecision(allowed=True)
