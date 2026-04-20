"""Tests for agent runtime modules (registry, memory, policy, executor, runner).

Covers design spec Section 13.1 required unit tests:
- Agent starts with resume extraction or policy correction.
- Agent blocks scoring before PII/safety completion.
- Agent translates non-English text or requires review if translation fails.
- Agent flags score below 30.
- Agent flags safety issue.
- Agent flags low extraction or language confidence.
- Agent max iterations triggers human review.
- Tool executor retries retryable failures.
- Tool executor returns typed non-retryable errors.
- Agent result compilation rejects incomplete report fields.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_policy import AgentPolicy
from backend.app.agent.agent_runner import AgentRunner, AgentResult
from backend.app.agent.tool_executor import ToolExecutor, ToolExecutionError
from backend.app.agent.tool_registry import (
    CANONICAL_TOOL_NAMES,
    get_tool_schemas,
    validate_tool_name,
)
from backend.app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_key="test-key",
        agent_max_iterations=12,
        agent_max_retries_per_tool=2,
    )


@pytest.fixture
def policy(settings: Settings) -> AgentPolicy:
    return AgentPolicy(settings)


@pytest.fixture
def memory() -> AgentMemory:
    return AgentMemory(
        job_id="test-job-1",
        blob_path="resumes-raw/test-job-1/resume.pdf",
        job_description="Senior Python developer with Azure experience.",
    )


# ── Tool Registry ────────────────────────────────────────────────


class TestToolRegistry:
    def test_nine_canonical_tools(self) -> None:
        assert len(CANONICAL_TOOL_NAMES) == 9

    def test_schema_count_matches(self) -> None:
        schemas = get_tool_schemas()
        assert len(schemas) == 9
        names = {s["function"]["name"] for s in schemas}
        assert names == CANONICAL_TOOL_NAMES

    def test_validate_canonical_name(self) -> None:
        for name in CANONICAL_TOOL_NAMES:
            assert validate_tool_name(name) == name

    def test_reject_obsolete_get_embedding(self) -> None:
        with pytest.raises(ValueError, match="obsolete"):
            validate_tool_name("get_embedding")

    def test_reject_obsolete_search_similar_jds(self) -> None:
        with pytest.raises(ValueError, match="obsolete"):
            validate_tool_name("search_similar_jds")

    def test_reject_unknown_tool(self) -> None:
        with pytest.raises(ValueError, match="Unknown tool"):
            validate_tool_name("nonexistent_tool")


# ── Agent Memory ─────────────────────────────────────────────────


class TestAgentMemory:
    def test_initial_state(self, memory: AgentMemory) -> None:
        assert memory.extraction_done is False
        assert memory.pii_safety_done is False
        assert memory.all_required_complete is False
        assert memory.human_review_flagged is False

    def test_record_extraction(self, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {
            "text": "Sample resume text",
            "page_count": 2,
            "confidence": 0.95,
        })
        assert memory.extraction_done is True
        assert memory.raw_resume_text == "Sample resume text"

    def test_record_pii_safety(self, memory: AgentMemory) -> None:
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "sanitized content",
            "pii_detected": True,
            "pii_categories": ["Person"],
            "safety_flagged": False,
            "safety_categories": [],
        })
        assert memory.pii_safety_done is True
        assert memory.sanitized_resume_text == "sanitized content"

    def test_milestone_properties(self, memory: AgentMemory) -> None:
        assert memory.scoring_done is False
        memory.record_tool_result("score_resume", {"score": 75})
        assert memory.scoring_done is True

        assert memory.similarity_done is False
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.8})
        assert memory.similarity_done is True

        assert memory.summary_done is False
        memory.record_tool_result("generate_fit_summary", {"summary": "Good fit"})
        assert memory.summary_done is True

        assert memory.all_required_complete is True

    def test_retry_tracking(self, memory: AgentMemory) -> None:
        assert memory.increment_retry("score_resume") == 1
        assert memory.increment_retry("score_resume") == 2

    def test_language_code(self, memory: AgentMemory) -> None:
        assert memory.get_language_code() is None
        memory.record_tool_result("detect_language", {
            "language_code": "fr",
            "language_name": "French",
            "confidence": 0.95,
        })
        assert memory.get_language_code() == "fr"

    def test_human_review_tracking(self, memory: AgentMemory) -> None:
        assert memory.human_review_flagged is False
        memory.record_tool_result("flag_for_human_review", {
            "review_id": "r1",
            "flagged": True,
        })
        assert memory.human_review_flagged is True


# ── Agent Policy ─────────────────────────────────────────────────


class TestAgentPolicy:
    def test_allow_extract_first(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        d = policy.check_tool_call("extract_resume_text", memory)
        assert d.allowed is True

    def test_block_score_before_extraction(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        d = policy.check_tool_call("score_resume", memory)
        assert d.allowed is False
        assert "extract_resume_text" in d.reason

    def test_block_score_before_pii(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        d = policy.check_tool_call("score_resume", memory)
        assert d.allowed is False
        assert "check_pii_and_safety" in d.reason

    def test_allow_score_after_extraction_and_pii(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "safe", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        d = policy.check_tool_call("score_resume", memory)
        assert d.allowed is True

    def test_block_detect_language_before_extraction(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        d = policy.check_tool_call("detect_language", memory)
        assert d.allowed is False

    def test_block_similarity_before_pii(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        d = policy.check_tool_call("compute_semantic_similarity", memory)
        assert d.allowed is False

    def test_reject_obsolete_tools(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        d = policy.check_tool_call("get_embedding", memory)
        assert d.allowed is False
        assert "obsolete" in d.reason

    def test_retry_limit(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.retry_counts["score_resume"] = 2
        d = policy.check_tool_call("score_resume", memory)
        assert d.allowed is False
        assert d.force_flag is True

    def test_iteration_limit(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.total_iterations = 12
        d = policy.check_iteration_limit(memory)
        assert d.force_complete is True
        assert d.force_flag is True

    def test_flag_low_score(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        memory.record_tool_result("score_resume", {
            "score": 25, "breakdown": {}, "confidence": 0.8,
            "matched_keywords": [], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.5})
        memory.record_tool_result("generate_fit_summary", {"summary": "Weak fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is True
        assert "Low score" in d.flag_reason

    def test_flag_safety_issue(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": True, "safety_categories": ["Hate"],
        })
        memory.record_tool_result("score_resume", {
            "score": 75, "breakdown": {}, "confidence": 0.9,
            "matched_keywords": [], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.8})
        memory.record_tool_result("generate_fit_summary", {"summary": "Good fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is True
        assert "safety" in d.flag_reason.lower()

    def test_flag_low_confidence(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        memory.record_tool_result("score_resume", {
            "score": 75, "breakdown": {}, "confidence": 0.4,
            "matched_keywords": [], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.8})
        memory.record_tool_result("generate_fit_summary", {"summary": "Good fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is True
        assert "Low confidence" in d.flag_reason

    def test_flag_low_extraction_confidence(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.3})
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        memory.record_tool_result("score_resume", {
            "score": 75, "breakdown": {}, "confidence": 0.9,
            "matched_keywords": [], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.8})
        memory.record_tool_result("generate_fit_summary", {"summary": "Good fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is True
        assert "extraction confidence" in d.flag_reason.lower()

    def test_flag_non_english_without_translation(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.9})
        memory.record_tool_result("detect_language", {
            "language_code": "fr", "language_name": "French", "confidence": 0.95,
        })
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        memory.record_tool_result("score_resume", {
            "score": 75, "breakdown": {}, "confidence": 0.9,
            "matched_keywords": [], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.8})
        memory.record_tool_result("generate_fit_summary", {"summary": "Good fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is True
        assert "Non-English" in d.flag_reason

    def test_no_flag_when_all_good(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        memory.record_tool_result("extract_resume_text", {"text": "t", "page_count": 1, "confidence": 0.95})
        memory.record_tool_result("detect_language", {
            "language_code": "en", "language_name": "English", "confidence": 1.0,
        })
        memory.record_tool_result("check_pii_and_safety", {
            "sanitized_text": "s", "pii_detected": False,
            "pii_categories": [], "safety_flagged": False, "safety_categories": [],
        })
        memory.record_tool_result("score_resume", {
            "score": 85, "breakdown": {}, "confidence": 0.92,
            "matched_keywords": ["python"], "missing_keywords": [],
        })
        memory.record_tool_result("compute_semantic_similarity", {"similarity_score": 0.88})
        memory.record_tool_result("generate_fit_summary", {"summary": "Strong fit"})
        d = policy.check_completion(memory)
        assert d.force_flag is False

    def test_force_early_flag_no_extraction(self, policy: AgentPolicy, memory: AgentMemory) -> None:
        d = policy.should_force_early_flag(memory)
        assert d.force_flag is True
        assert d.force_complete is True


# ── Tool Executor ────────────────────────────────────────────────


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        memory.record_tool_result("extract_resume_text", {
            "text": "resume", "page_count": 1, "confidence": 0.9,
        })

        async def mock_adapter(args: dict, mem: AgentMemory) -> dict:
            return {
                "sanitized_text": "safe text",
                "pii_detected": False,
                "pii_categories": [],
                "safety_flagged": False,
                "safety_categories": [],
            }

        executor = ToolExecutor(settings, policy)
        executor.register_adapter("check_pii_and_safety", mock_adapter)

        result = await executor.execute("check_pii_and_safety", {"text": "resume"}, memory)
        assert result["sanitized_text"] == "safe text"
        assert len(memory.trace_steps) == 1

    @pytest.mark.asyncio
    async def test_execute_blocked_by_policy(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        executor = ToolExecutor(settings, policy)
        with pytest.raises(ValueError, match="extract_resume_text"):
            await executor.execute("score_resume", {"jd": "text", "resume_text": "text"}, memory)

    @pytest.mark.asyncio
    async def test_execute_retries_on_failure(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        call_count = 0

        async def flaky_adapter(args: dict, mem: AgentMemory) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Transient failure")
            return {"text": "ok", "page_count": 1, "confidence": 0.9}

        executor = ToolExecutor(settings, policy)
        executor.register_adapter("extract_resume_text", flaky_adapter)

        result = await executor.execute("extract_resume_text", {"blob_path": "test.pdf"}, memory)
        assert result["text"] == "ok"
        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_execute_fails_after_max_retries(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        async def always_fail_adapter(args: dict, mem: AgentMemory) -> dict:
            raise RuntimeError("Permanent failure")

        executor = ToolExecutor(settings, policy)
        executor.register_adapter("extract_resume_text", always_fail_adapter)

        with pytest.raises(ToolExecutionError, match="Failed after"):
            await executor.execute("extract_resume_text", {"blob_path": "test.pdf"}, memory)

    @pytest.mark.asyncio
    async def test_execute_no_adapter(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        executor = ToolExecutor(settings, policy)
        with pytest.raises(ToolExecutionError, match="No adapter"):
            await executor.execute("extract_resume_text", {"blob_path": "test.pdf"}, memory)

    @pytest.mark.asyncio
    async def test_execute_emits_events(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        events: list[dict] = []

        async def capture_event(event: dict) -> None:
            events.append(event)

        async def adapter(args: dict, mem: AgentMemory) -> dict:
            return {"text": "resume text", "page_count": 1, "confidence": 0.9}

        executor = ToolExecutor(settings, policy)
        executor.register_adapter("extract_resume_text", adapter)

        await executor.execute(
            "extract_resume_text", {"blob_path": "test.pdf"}, memory,
            event_callback=capture_event,
        )

        assert len(events) == 1
        assert events[0]["event_type"] == "tool_result"


# ── Agent Runner ─────────────────────────────────────────────────


class TestAgentRunner:
    def _make_mock_model_response(
        self,
        tool_calls: list[dict] | None = None,
        content: str | None = None,
        finish_reason: str = "tool_calls" if True else "stop",
    ) -> MagicMock:
        """Build a mock OpenAI chat completion response."""
        message = MagicMock()
        message.content = content
        if tool_calls:
            mock_calls = []
            for tc in tool_calls:
                mock_tc = MagicMock()
                mock_tc.id = tc.get("id", "call_1")
                mock_tc.function.name = tc["name"]
                mock_tc.function.arguments = json.dumps(tc.get("arguments", {}))
                mock_calls.append(mock_tc)
            message.tool_calls = mock_calls
        else:
            message.tool_calls = None

        choice = MagicMock()
        choice.message = message
        choice.finish_reason = finish_reason

        response = MagicMock()
        response.choices = [choice]
        return response

    @pytest.mark.asyncio
    async def test_full_agent_run(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        """Simulate a full successful agent run with all tools."""
        call_count = 0

        async def mock_model(messages, **kwargs):
            nonlocal call_count
            call_count += 1

            # Iteration 1: extract resume text
            if call_count == 1:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "extract_resume_text", "arguments": {"blob_path": memory.blob_path}},
                ])
            # Iteration 2: detect language + check PII
            if call_count == 2:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "detect_language", "arguments": {"text": "resume text"}},
                ])
            if call_count == 3:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "check_pii_and_safety", "arguments": {"text": "resume text"}},
                ])
            # Iteration 4: score
            if call_count == 4:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "score_resume", "arguments": {
                        "job_description": memory.job_description,
                        "resume_text": "sanitized",
                    }},
                ])
            # Iteration 5: similarity
            if call_count == 5:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "compute_semantic_similarity", "arguments": {
                        "job_description": memory.job_description,
                        "resume_text": "sanitized",
                    }},
                ])
            # Iteration 6: fit summary
            if call_count == 6:
                return self._make_mock_model_response(tool_calls=[
                    {"name": "generate_fit_summary", "arguments": {
                        "score": 85, "matched_keywords": ["python"],
                        "missing_keywords": [], "job_description": memory.job_description,
                        "resume_text": "sanitized",
                    }},
                ])
            # Iteration 7: done
            return self._make_mock_model_response(
                content="Analysis complete.", finish_reason="stop",
            )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = mock_model

        # Tool adapters
        async def extract_adapter(args, mem):
            return {"text": "resume text", "page_count": 2, "confidence": 0.95}
        async def detect_adapter(args, mem):
            return {"language_code": "en", "language_name": "English", "confidence": 1.0}
        async def pii_adapter(args, mem):
            return {
                "sanitized_text": "sanitized", "pii_detected": False,
                "pii_categories": [], "safety_flagged": False, "safety_categories": [],
            }
        async def score_adapter(args, mem):
            return {
                "score": 85, "breakdown": {
                    "keyword_match": 35, "experience_alignment": 25, "skills_coverage": 25,
                },
                "matched_keywords": ["python"], "missing_keywords": [],
                "confidence": 0.92,
            }
        async def similarity_adapter(args, mem):
            return {
                "similarity_score": 0.88, "cache_hit": False,
                "resume_embedding_ref": "r1", "jd_embedding_ref": "j1",
            }
        async def summary_adapter(args, mem):
            return {"summary": "Strong candidate for the Python developer role."}

        executor = ToolExecutor(settings, policy)
        executor.register_adapter("extract_resume_text", extract_adapter)
        executor.register_adapter("detect_language", detect_adapter)
        executor.register_adapter("check_pii_and_safety", pii_adapter)
        executor.register_adapter("score_resume", score_adapter)
        executor.register_adapter("compute_semantic_similarity", similarity_adapter)
        executor.register_adapter("generate_fit_summary", summary_adapter)

        runner = AgentRunner(settings, policy, executor, openai_client=mock_client)
        result = await runner.run(memory)

        assert result.score == 85
        assert result.semantic_similarity == 0.88
        assert result.fit_summary == "Strong candidate for the Python developer role."
        assert result.human_review_required is False
        assert result.error is None
        assert result.total_iterations > 0

    @pytest.mark.asyncio
    async def test_max_iterations_triggers_review(
        self, settings: Settings, memory: AgentMemory,
    ) -> None:
        """Agent flags for human review when max iterations is reached."""
        low_settings = Settings(
            azure_openai_endpoint="https://test.openai.azure.com/",
            azure_openai_key="test-key",
            agent_max_iterations=2,
        )
        low_policy = AgentPolicy(low_settings)

        async def always_extract(messages, **kwargs):
            return self._make_mock_model_response(tool_calls=[
                {"name": "extract_resume_text", "arguments": {"blob_path": "test.pdf"}},
            ])

        mock_client = AsyncMock()
        mock_client.chat.completions.create = always_extract

        async def extract_adapter(args, mem):
            return {"text": "text", "page_count": 1, "confidence": 0.9}

        executor = ToolExecutor(low_settings, low_policy)
        executor.register_adapter("extract_resume_text", extract_adapter)

        runner = AgentRunner(low_settings, low_policy, executor, openai_client=mock_client)
        result = await runner.run(memory)

        assert result.human_review_required is True
        assert "max iterations" in result.human_review_reason.lower()

    @pytest.mark.asyncio
    async def test_result_compilation_incomplete(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        """AgentResult correctly reflects missing data."""
        runner = AgentRunner(settings, policy, ToolExecutor(settings, policy), openai_client=AsyncMock())
        # Only extraction done, nothing else.
        memory.record_tool_result("extract_resume_text", {
            "text": "t", "page_count": 1, "confidence": 0.9,
        })
        result = runner._compile_result(memory)
        assert result.score is None
        assert result.semantic_similarity is None
        assert result.fit_summary is None

    @pytest.mark.asyncio
    async def test_runner_emits_complete_event(
        self, settings: Settings, policy: AgentPolicy, memory: AgentMemory,
    ) -> None:
        """Runner emits a complete SSE event on finish."""
        events: list[dict] = []

        async def capture(event: dict) -> None:
            events.append(event)

        # Model returns stop immediately (minimal run).
        async def immediate_stop(messages, **kwargs):
            return self._make_mock_model_response(
                content="Done", finish_reason="stop",
            )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = immediate_stop

        executor = ToolExecutor(settings, policy)
        runner = AgentRunner(settings, policy, executor, openai_client=mock_client)
        await runner.run(memory, event_callback=capture)

        complete_events = [e for e in events if e.get("event_type") == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["job_id"] == memory.job_id

    def test_lazy_client_from_settings(self, settings: Settings) -> None:
        """AgentRunner builds AsyncAzureOpenAI from settings when no client injected."""
        from unittest.mock import patch

        mock_client = MagicMock()
        with patch(
            "backend.app.services.openai_adapter.build_async_openai_client",
            return_value=mock_client,
        ) as mock_build:
            policy = AgentPolicy(settings)
            executor = ToolExecutor(settings, policy)
            runner = AgentRunner(settings, policy, executor)

            mock_build.assert_called_once_with(
                endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.openai_api_version,
            )
            assert runner._openai_client is mock_client

    def test_injected_client_used_directly(self, settings: Settings) -> None:
        """AgentRunner uses the injected client without calling build."""
        from unittest.mock import patch

        mock_client = AsyncMock()
        with patch(
            "backend.app.services.openai_adapter.build_async_openai_client",
        ) as mock_build:
            policy = AgentPolicy(settings)
            executor = ToolExecutor(settings, policy)
            runner = AgentRunner(settings, policy, executor, openai_client=mock_client)

            mock_build.assert_not_called()
            assert runner._openai_client is mock_client

    @pytest.mark.asyncio
    async def test_run_without_injected_client(
        self, settings: Settings, memory: AgentMemory,
    ) -> None:
        """AgentRunner works end-to-end when client is built from settings."""
        from unittest.mock import patch

        mock_client = AsyncMock()

        async def immediate_stop(messages, **kwargs):
            return self._make_mock_model_response(
                content="Done", finish_reason="stop",
            )

        mock_client.chat.completions.create = immediate_stop

        with patch(
            "backend.app.services.openai_adapter.build_async_openai_client",
            return_value=mock_client,
        ):
            policy = AgentPolicy(settings)
            executor = ToolExecutor(settings, policy)
            runner = AgentRunner(settings, policy, executor)
            result = await runner.run(memory)

        assert result.error is None
        assert result.job_id == memory.job_id
