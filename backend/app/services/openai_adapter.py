"""Azure OpenAI adapter — scoring, fit summary, and embeddings.

Design spec Section 4.3: used by score_resume, generate_fit_summary,
and compute_semantic_similarity tools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import (
    ScoreResumeInput,
    ScoreResumeOutput,
    ScoreResumeBreakdown,
    GenerateFitSummaryInput,
    GenerateFitSummaryOutput,
)

logger = logging.getLogger(__name__)

_SCORING_SYSTEM_PROMPT = (
    "You are an ATS resume scoring engine. Score the resume against the job "
    "description on a 0-100 scale. Breakdown weights: keyword_match (0-40), "
    "experience_alignment (0-30), skills_coverage (0-30). The three breakdown "
    "values must sum to the total score. Also list matched_keywords, "
    "missing_keywords, and confidence (0.0-1.0). "
    "Respond with valid JSON only."
)

_FIT_SUMMARY_SYSTEM_PROMPT = (
    "You are an ATS assistant. Write 2-3 plain-English sentences for a "
    "recruiter explaining how well the candidate fits the role. Do not "
    "expose protected attributes, raw PII, or unsupported claims."
)


def build_async_openai_client(
    endpoint: str,
    api_key: str | None,
    api_version: str,
) -> Any:
    """Build an AsyncAzureOpenAI client from connection parameters.

    Shared by OpenAIAdapter and AgentRunner so connection logic lives
    in one place.
    """
    from openai import AsyncAzureOpenAI

    kwargs: dict[str, Any] = {
        "azure_endpoint": endpoint,
        "api_version": api_version,
    }
    if api_key:
        kwargs["api_key"] = api_key
    return AsyncAzureOpenAI(**kwargs)


class OpenAIAdapter:
    """Wraps Azure OpenAI for scoring, fit summary, and embeddings."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.azure_openai_endpoint
        self._key = settings.azure_openai_key
        self._chat_deployment = settings.chat_model_deployment_name
        self._embedding_deployment = settings.embedding_model_deployment_name
        self._api_version = settings.openai_api_version

    async def score_resume(
        self,
        input_data: ScoreResumeInput,
        *,
        client: Any | None = None,
    ) -> ScoreResumeOutput:
        """Score a resume against a job description using chat completion."""
        if client is None:
            client = self._build_chat_client()

        logger.info("Scoring resume against JD (JD length=%d)", len(input_data.job_description))

        user_message = (
            f"Job Description:\n{input_data.job_description}\n\n"
            f"Resume:\n{input_data.resume_text}"
        )

        response = await client.chat.completions.create(
            model=self._chat_deployment,
            messages=[
                {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # Handle both nested {"breakdown": {...}} and flat layout.
        if "breakdown" in parsed and isinstance(parsed["breakdown"], dict):
            bd = parsed["breakdown"]
        else:
            bd = {
                "keyword_match": parsed.get("keyword_match", 0),
                "experience_alignment": parsed.get("experience_alignment", 0),
                "skills_coverage": parsed.get("skills_coverage", 0),
            }

        return ScoreResumeOutput(
            score=parsed["score"],
            breakdown=ScoreResumeBreakdown(**bd),
            matched_keywords=parsed.get("matched_keywords", []),
            missing_keywords=parsed.get("missing_keywords", []),
            confidence=parsed.get("confidence", 0.5),
        )

    async def generate_fit_summary(
        self,
        input_data: GenerateFitSummaryInput,
        *,
        client: Any | None = None,
    ) -> GenerateFitSummaryOutput:
        """Generate a 2-3 sentence recruiter-readable fit summary."""
        if client is None:
            client = self._build_chat_client()

        logger.info("Generating fit summary (score=%d)", input_data.score)

        user_message = (
            f"Score: {input_data.score}/100\n"
            f"Matched keywords: {', '.join(input_data.matched_keywords)}\n"
            f"Missing keywords: {', '.join(input_data.missing_keywords)}\n"
            f"Job Description:\n{input_data.job_description}\n\n"
            f"Resume:\n{input_data.resume_text}"
        )

        response = await client.chat.completions.create(
            model=self._chat_deployment,
            messages=[
                {"role": "system", "content": _FIT_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )

        return GenerateFitSummaryOutput(
            summary=response.choices[0].message.content,
        )

    async def get_embedding(
        self,
        text: str,
        *,
        client: Any | None = None,
    ) -> list[float]:
        """Get embedding vector for text. Returns the embedding array."""
        if client is None:
            client = self._build_embedding_client()

        logger.info("Computing embedding (text length=%d)", len(text))

        response = await client.embeddings.create(
            model=self._embedding_deployment,
            input=text,
        )

        return response.data[0].embedding

    def _build_chat_client(self) -> Any:
        return build_async_openai_client(
            endpoint=self._endpoint,
            api_key=self._key,
            api_version=self._api_version,
        )

    def _build_embedding_client(self) -> Any:
        # Same client works for both chat and embeddings.
        return self._build_chat_client()
