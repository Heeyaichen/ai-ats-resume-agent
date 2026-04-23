"""Tool adapter wiring — connects service adapters to the tool executor.

Creates async callables with signature `(args: dict, memory: AgentMemory) -> dict`
for each of the 9 canonical tools, bridging between the tool executor's
dict-based interface and the service adapters' Pydantic model interface.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from backend.app.agent.agent_memory import AgentMemory
from backend.app.config import Settings

logger = logging.getLogger(__name__)


def register_all_adapters(
    executor: Any,
    settings: Settings,
    *,
    cosmos_adapter: Any | None = None,
    blob_adapter: Any | None = None,
) -> None:
    """Register all 9 canonical tool adapters on the given executor.

    Each adapter is an async callable: (args: dict, memory: AgentMemory) -> dict.
    Service adapters are created lazily only when their settings are available.
    """
    executor.register_adapter("extract_resume_text", _make_extract_adapter(settings, blob_adapter))
    executor.register_adapter("detect_language", _make_detect_language_adapter(settings))
    executor.register_adapter("translate_text", _make_translate_adapter(settings))
    executor.register_adapter("check_pii_and_safety", _make_pii_safety_adapter(settings))
    executor.register_adapter("score_resume", _make_score_adapter(settings))
    executor.register_adapter("compute_semantic_similarity", _make_similarity_adapter(settings))
    executor.register_adapter("search_similar_candidates", _make_search_adapter(settings))
    executor.register_adapter("flag_for_human_review", _make_flag_adapter(settings, cosmos_adapter))
    executor.register_adapter("generate_fit_summary", _make_fit_summary_adapter(settings))


# ── extract_resume_text ─────────────────────────────────────────────


def _make_extract_adapter(settings: Settings, blob_adapter: Any | None) -> Any:
    async def extract_resume_text(args: dict, memory: AgentMemory) -> dict:
        from backend.app.models.tools import ExtractResumeTextInput

        blob_path = args.get("blob_path", memory.blob_path)
        input_data = ExtractResumeTextInput(blob_path=blob_path)

        # Download blob bytes first.
        blob_bytes: bytes | None = None
        if blob_adapter is not None:
            blob_bytes = await blob_adapter.download_resume(blob_path)

        if settings.document_intelligence_endpoint:
            from backend.app.services.document_intelligence import DocumentIntelligenceAdapter
            adapter = DocumentIntelligenceAdapter(settings)
            result = await adapter.extract_resume_text(input_data, blob_bytes=blob_bytes)
            return result.model_dump()

        # Fallback: return placeholder so agent can continue.
        logger.warning("Document Intelligence not configured, returning placeholder extraction")
        return {"text": "", "page_count": 0, "confidence": 0.0}

    return extract_resume_text


# ── detect_language ──────────────────────────────────────────────────


def _make_detect_language_adapter(settings: Settings) -> Any:
    async def detect_language(args: dict, memory: AgentMemory) -> dict:
        text = args.get("text", "")[:500]  # Design spec: first 500 chars.

        if settings.translator_endpoint:
            from backend.app.services.translator import TranslatorAdapter
            from backend.app.models.tools import DetectLanguageInput

            adapter = TranslatorAdapter(settings)
            input_data = DetectLanguageInput(text=text)
            result = await adapter.detect_language(input_data)
            return result.model_dump()

        # Default to English if translator not configured.
        return {"language_code": "en", "language_name": "English", "confidence": 1.0}

    return detect_language


# ── translate_text ───────────────────────────────────────────────────


def _make_translate_adapter(settings: Settings) -> Any:
    async def translate_text(args: dict, memory: AgentMemory) -> dict:
        if settings.translator_endpoint:
            from backend.app.services.translator import TranslatorAdapter
            from backend.app.models.tools import TranslateTextInput

            adapter = TranslatorAdapter(settings)
            input_data = TranslateTextInput(
                text=args.get("text", ""),
                source_language=args.get("source_language", "unknown"),
            )
            result = await adapter.translate_text(input_data)
            return result.model_dump()

        return {"translated_text": args.get("text", ""), "source_language": args.get("source_language", "")}

    return translate_text


# ── check_pii_and_safety ─────────────────────────────────────────────


def _make_pii_safety_adapter(settings: Settings) -> Any:
    async def check_pii_and_safety(args: dict, memory: AgentMemory) -> dict:
        text = args.get("text", "")

        if settings.language_endpoint or settings.content_safety_endpoint:
            from backend.app.services.pii_safety import PIISafetyService
            from backend.app.models.tools import CheckPIIAndSafetyInput

            service = PIISafetyService(settings)
            input_data = CheckPIIAndSafetyInput(text=text)
            result = await service.check(input_data)
            return result.model_dump()

        # Pass-through if services not configured.
        return {
            "sanitized_text": text,
            "pii_detected": False,
            "pii_categories": [],
            "safety_flagged": False,
            "safety_categories": [],
        }

    return check_pii_and_safety


# ── score_resume ─────────────────────────────────────────────────────


def _make_score_adapter(settings: Settings) -> Any:
    async def score_resume(args: dict, memory: AgentMemory) -> dict:
        from backend.app.services.openai_adapter import OpenAIAdapter
        from backend.app.models.tools import ScoreResumeInput

        adapter = OpenAIAdapter(settings)
        input_data = ScoreResumeInput(
            job_description=args.get("job_description", memory.job_description),
            resume_text=args.get("resume_text", ""),
        )
        result = await adapter.score_resume(input_data)
        return result.model_dump()

    return score_resume


# ── compute_semantic_similarity ──────────────────────────────────────


def _make_similarity_adapter(settings: Settings) -> Any:
    async def compute_semantic_similarity(args: dict, memory: AgentMemory) -> dict:
        from backend.app.services.openai_adapter import OpenAIAdapter

        jd_text = args.get("job_description", memory.job_description)
        resume_text = args.get("resume_text", "")
        cache_hit = False

        # Check Redis cache.
        if settings.redis_url:
            from backend.app.services.redis_cache import RedisCacheAdapter
            cache = RedisCacheAdapter(settings)
            cached = await cache.get_similarity(jd_text, resume_text)
            if cached is not None:
                cache_hit = True
                return {
                    "similarity_score": cached,
                    "cache_hit": True,
                    "resume_embedding_ref": "cached",
                    "jd_embedding_ref": "cached",
                }

        # Compute embeddings.
        adapter = OpenAIAdapter(settings)
        jd_embedding = await adapter.get_embedding(jd_text)
        resume_embedding = await adapter.get_embedding(resume_text)

        # Cosine similarity.
        dot = sum(a * b for a, b in zip(jd_embedding, resume_embedding))
        norm_jd = math.sqrt(sum(a * a for a in jd_embedding))
        norm_r = math.sqrt(sum(b * b for b in resume_embedding))
        similarity = dot / (norm_jd * norm_r) if norm_jd > 0 and norm_r > 0 else 0.0

        # Cache the result.
        if settings.redis_url:
            from backend.app.services.redis_cache import RedisCacheAdapter
            cache = RedisCacheAdapter(settings)
            await cache.set_similarity(jd_text, resume_text, similarity)

        return {
            "similarity_score": similarity,
            "cache_hit": cache_hit,
            "resume_embedding_ref": f"emb:{memory.job_id}:resume",
            "jd_embedding_ref": f"emb:{memory.job_id}:jd",
        }

    return compute_semantic_similarity


# ── search_similar_candidates ────────────────────────────────────────


def _make_search_adapter(settings: Settings) -> Any:
    async def search_similar_candidates(args: dict, memory: AgentMemory) -> dict:
        if not settings.search_endpoint:
            logger.info("Search not configured, returning empty candidates")
            return {"similar_candidates": []}

        from backend.app.services.search import SearchAdapter
        from backend.app.models.tools import SearchSimilarCandidatesInput
        from backend.app.services.openai_adapter import OpenAIAdapter

        adapter = SearchAdapter(settings)
        input_data = SearchSimilarCandidatesInput(
            resume_embedding_ref=args.get("resume_embedding_ref", ""),
            top_k=args.get("top_k", 3),
        )

        # We need an embedding vector for search. Try to get it from
        # the sanitized resume text in memory.
        resume_text = memory.sanitized_resume_text or memory.raw_resume_text or ""
        if not resume_text:
            return {"similar_candidates": []}

        openai_adapter = OpenAIAdapter(settings)
        embedding = await openai_adapter.get_embedding(resume_text)

        result = await adapter.search_similar_candidates(input_data, embedding)
        return result.model_dump()

    return search_similar_candidates


# ── flag_for_human_review ────────────────────────────────────────────


def _make_flag_adapter(settings: Settings, cosmos_adapter: Any | None) -> Any:
    async def flag_for_human_review(args: dict, memory: AgentMemory) -> dict:
        from backend.app.models.tools import FlagForHumanReviewInput

        input_data = FlagForHumanReviewInput(
            job_id=args.get("job_id", memory.job_id),
            reason=args.get("reason", "Agent-initiated review flag"),
            severity=args.get("severity", "medium"),
        )

        if cosmos_adapter is not None:
            result = await cosmos_adapter.flag_for_human_review(input_data)
            return result.model_dump()

        # Fallback: return a local flag.
        import uuid
        return {"review_id": str(uuid.uuid4()), "flagged": True}

    return flag_for_human_review


# ── generate_fit_summary ─────────────────────────────────────────────


def _make_fit_summary_adapter(settings: Settings) -> Any:
    async def generate_fit_summary(args: dict, memory: AgentMemory) -> dict:
        from backend.app.services.openai_adapter import OpenAIAdapter
        from backend.app.models.tools import GenerateFitSummaryInput

        adapter = OpenAIAdapter(settings)
        input_data = GenerateFitSummaryInput(
            score=args.get("score", 0),
            matched_keywords=args.get("matched_keywords", []),
            missing_keywords=args.get("missing_keywords", []),
            job_description=args.get("job_description", memory.job_description),
            resume_text=args.get("resume_text", ""),
        )
        result = await adapter.generate_fit_summary(input_data)
        return result.model_dump()

    return generate_fit_summary
