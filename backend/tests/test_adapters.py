"""Tests for Azure service adapters with mocked SDK clients."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.config import Settings
from backend.app.models.tools import (
    ExtractResumeTextInput,
    ExtractResumeTextOutput,
    DetectLanguageInput,
    DetectLanguageOutput,
    TranslateTextInput,
    TranslateTextOutput,
    CheckPIIAndSafetyInput,
    CheckPIIAndSafetyOutput,
    ScoreResumeInput,
    ScoreResumeOutput,
    SearchSimilarCandidatesInput,
    SearchSimilarCandidatesOutput,
    FlagForHumanReviewInput,
    FlagForHumanReviewOutput,
    GenerateFitSummaryInput,
    GenerateFitSummaryOutput,
)
from backend.app.services.document_intelligence import DocumentIntelligenceAdapter
from backend.app.services.translator import TranslatorAdapter
from backend.app.services.language import LanguageAdapter
from backend.app.services.content_safety import ContentSafetyAdapter
from backend.app.services.openai_adapter import OpenAIAdapter
from backend.app.services.redis_cache import RedisCacheAdapter
from backend.app.services.search import SearchAdapter
from backend.app.services.cosmos import CosmosAdapter
from backend.app.services.blob_storage import BlobStorageAdapter
from backend.app.services.pii_safety import PIISafetyService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_key="test-key",
        document_intelligence_endpoint="https://test-di.cognitiveservices.azure.com",
        document_intelligence_key="di-key",
        translator_endpoint="https://api.cognitive.microsofttranslator.com",
        translator_key="trans-key",
        translator_region="swedencentral",
        language_endpoint="https://test-lang.cognitiveservices.azure.com",
        language_key="lang-key",
        content_safety_endpoint="https://test-cs.cognitiveservices.azure.com",
        content_safety_key="cs-key",
        cosmos_endpoint="https://test-cosmos.documents.azure.com:443/",
        cosmos_key="cosmos-key",
        storage_connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net",
        redis_url="redis://localhost:6379",
        search_endpoint="https://test-search.search.windows.net",
        search_key="search-key",
    )


# ── Document Intelligence ──────────────────────────────────────────


class TestDocumentIntelligenceAdapter:
    @pytest.mark.asyncio
    async def test_extract_resume_text(self, settings: Settings) -> None:
        mock_result = MagicMock()
        mock_result.content = "Extracted resume text content"
        mock_result.pages = [MagicMock(), MagicMock()]

        mock_poller = AsyncMock()
        mock_poller.result.return_value = mock_result

        mock_client = AsyncMock()
        mock_client.begin_analyze_document.return_value = mock_poller

        adapter = DocumentIntelligenceAdapter(settings)
        output = await adapter.extract_resume_text(
            ExtractResumeTextInput(blob_path="resumes-raw/abc/resume.pdf"),
            blob_bytes=b"%PDF-1.4 fake",
            client=mock_client,
        )

        assert isinstance(output, ExtractResumeTextOutput)
        assert output.text == "Extracted resume text content"
        assert output.page_count == 2
        assert output.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_extract_requires_blob_bytes(self, settings: Settings) -> None:
        adapter = DocumentIntelligenceAdapter(settings)
        with pytest.raises(ValueError, match="blob_bytes"):
            await adapter.extract_resume_text(
                ExtractResumeTextInput(blob_path="resumes-raw/abc/resume.pdf"),
                client=AsyncMock(),
            )


# ── Translator ──────────────────────────────────────────────────────


class TestTranslatorAdapter:
    @pytest.mark.asyncio
    async def test_detect_language_english(self, settings: Settings) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = [
            {"language": "en", "score": 1.0}
        ]

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        adapter = TranslatorAdapter(settings)
        with patch("httpx.AsyncClient", return_value=mock_http):
            output = await adapter.detect_language(
                DetectLanguageInput(text="Hello, I am a software engineer."),
            )

        assert isinstance(output, DetectLanguageOutput)
        assert output.language_code == "en"
        assert output.confidence == 1.0
        # Verify 500-char limit applied
        call_body = mock_http.post.call_args[1]["json"]
        assert len(call_body[0]["text"]) <= 500

    @pytest.mark.asyncio
    async def test_detect_language_truncates_long_text(self, settings: Settings) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = [
            {"language": "fr", "score": 0.95}
        ]

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        adapter = TranslatorAdapter(settings)
        long_text = "x" * 1000
        with patch("httpx.AsyncClient", return_value=mock_http):
            await adapter.detect_language(
                DetectLanguageInput(text=long_text),
            )

        call_body = mock_http.post.call_args[1]["json"]
        assert len(call_body[0]["text"]) == 500

    @pytest.mark.asyncio
    async def test_translate_text(self, settings: Settings) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = [
            {"translations": [{"text": "Hello world", "to": "en"}]}
        ]

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        adapter = TranslatorAdapter(settings)
        with patch("httpx.AsyncClient", return_value=mock_http):
            output = await adapter.translate_text(
                TranslateTextInput(text="Bonjour le monde", source_language="fr"),
            )

        assert isinstance(output, TranslateTextOutput)
        assert output.translated_text == "Hello world"
        assert output.source_language == "fr"


# ── Language (PII) ──────────────────────────────────────────────────


class TestLanguageAdapter:
    @pytest.mark.asyncio
    async def test_pii_detected(self, settings: Settings) -> None:
        entity = MagicMock()
        entity.category = "Person"
        mock_result = MagicMock()
        mock_result.entities = [entity]
        mock_result.redacted_text = "Hello [REDACTED]"

        mock_client = AsyncMock()
        mock_client.recognize_pii_entities.return_value = [mock_result]

        adapter = LanguageAdapter(settings)
        output = await adapter.recognize_pii(
            CheckPIIAndSafetyInput(text="Hello John Doe"),
            client=mock_client,
        )

        assert isinstance(output, CheckPIIAndSafetyOutput)
        assert output.pii_detected is True
        assert "Person" in output.pii_categories
        assert output.sanitized_text == "Hello [REDACTED]"
        assert output.safety_flagged is False

    @pytest.mark.asyncio
    async def test_no_pii(self, settings: Settings) -> None:
        mock_result = MagicMock()
        mock_result.entities = []

        mock_client = AsyncMock()
        mock_client.recognize_pii_entities.return_value = [mock_result]

        adapter = LanguageAdapter(settings)
        output = await adapter.recognize_pii(
            CheckPIIAndSafetyInput(text="No sensitive data here"),
            client=mock_client,
        )

        assert output.pii_detected is False
        assert output.pii_categories == []


# ── Content Safety ──────────────────────────────────────────────────


class TestContentSafetyAdapter:
    @pytest.mark.asyncio
    async def test_safe_content(self, settings: Settings) -> None:
        mock_response = MagicMock()
        mock_response.categories_analysis = []

        mock_client = MagicMock()
        mock_client.analyze_text.return_value = mock_response

        adapter = ContentSafetyAdapter(settings)
        output = await adapter.analyze_text("Normal resume text", client=mock_client)

        assert output.safety_flagged is False
        assert output.safety_categories == []

    @pytest.mark.asyncio
    async def test_unsafe_content(self, settings: Settings) -> None:
        analysis = MagicMock()
        analysis.category = "Hate"
        analysis.severity = 2
        mock_response = MagicMock()
        mock_response.categories_analysis = [analysis]

        mock_client = MagicMock()
        mock_client.analyze_text.return_value = mock_response

        adapter = ContentSafetyAdapter(settings)
        output = await adapter.analyze_text("Bad content", client=mock_client)

        assert output.safety_flagged is True
        assert "Hate" in output.safety_categories


# ── PII + Safety combined ──────────────────────────────────────────


class TestPIISafetyService:
    @pytest.mark.asyncio
    async def test_combined_pii_and_safety(self, settings: Settings) -> None:
        # PII mock
        entity = MagicMock()
        entity.category = "EmailAddress"
        pii_result = MagicMock()
        pii_result.entities = [entity]
        pii_result.redacted_text = "Contact: [REDACTED]"

        mock_lang_client = AsyncMock()
        mock_lang_client.recognize_pii_entities.return_value = [pii_result]

        # Safety mock (safe) — sync client, use MagicMock
        safety_response = MagicMock()
        safety_response.categories_analysis = []

        mock_safety_client = MagicMock()
        mock_safety_client.analyze_text.return_value = safety_response

        service = PIISafetyService(settings)
        output = await service.check(
            CheckPIIAndSafetyInput(text="Contact: john@example.com"),
            language_client=mock_lang_client,
            safety_client=mock_safety_client,
        )

        assert output.pii_detected is True
        assert output.safety_flagged is False
        assert "EmailAddress" in output.pii_categories
        assert output.sanitized_text == "Contact: [REDACTED]"


# ── OpenAI (scoring, fit summary, embeddings) ──────────────────────


class TestOpenAIAdapter:
    @pytest.mark.asyncio
    async def test_score_resume(self, settings: Settings) -> None:
        score_json = json.dumps({
            "score": 75,
            "breakdown": {"keyword_match": 30, "experience_alignment": 25, "skills_coverage": 20},
            "matched_keywords": ["python", "fastapi"],
            "missing_keywords": ["azure"],
            "confidence": 0.85,
        })
        mock_message = MagicMock()
        mock_message.content = score_json
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        adapter = OpenAIAdapter(settings)
        output = await adapter.score_resume(
            ScoreResumeInput(
                job_description="Python developer",
                resume_text="I know Python and FastAPI",
            ),
            client=mock_client,
        )

        assert isinstance(output, ScoreResumeOutput)
        assert output.score == 75
        assert output.breakdown.keyword_match == 30
        assert output.confidence == 0.85

    @pytest.mark.asyncio
    async def test_generate_fit_summary(self, settings: Settings) -> None:
        mock_message = MagicMock()
        mock_message.content = "The candidate is a strong fit."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response

        adapter = OpenAIAdapter(settings)
        output = await adapter.generate_fit_summary(
            GenerateFitSummaryInput(
                score=80,
                matched_keywords=["python"],
                missing_keywords=["docker"],
                job_description="Python dev",
                resume_text="Python dev",
            ),
            client=mock_client,
        )

        assert isinstance(output, GenerateFitSummaryOutput)
        assert "strong fit" in output.summary

    @pytest.mark.asyncio
    async def test_get_embedding(self, settings: Settings) -> None:
        mock_data = MagicMock()
        mock_data.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_data]

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response

        adapter = OpenAIAdapter(settings)
        embedding = await adapter.get_embedding("test text", client=mock_client)

        assert len(embedding) == 1536
        assert embedding[0] == 0.1


# ── Redis Cache ────────────────────────────────────────────────────


class TestRedisCacheAdapter:
    def test_key_formats(self, settings: Settings) -> None:
        adapter = RedisCacheAdapter(settings)

        emb_key = adapter._embedding_key("hello")
        assert emb_key.startswith("embedding:text-embedding-ada-002:")

        sim_key = adapter._similarity_key("jd text", "resume text")
        assert sim_key.startswith("similarity:text-embedding-ada-002:")

    def test_hash_deterministic(self, settings: Settings) -> None:
        adapter = RedisCacheAdapter(settings)
        h1 = adapter._hash("test")
        h2 = adapter._hash("test")
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, settings: Settings) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        adapter = RedisCacheAdapter(settings)
        adapter._client = mock_redis

        result = await adapter.get_embedding("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, settings: Settings) -> None:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([0.1, 0.2, 0.3])

        adapter = RedisCacheAdapter(settings)
        adapter._client = mock_redis

        result = await adapter.get_embedding("test")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_set_embedding(self, settings: Settings) -> None:
        mock_redis = AsyncMock()
        adapter = RedisCacheAdapter(settings)
        adapter._client = mock_redis

        await adapter.set_embedding("test", [0.1, 0.2])
        mock_redis.set.assert_called_once()
        args = mock_redis.set.call_args
        assert args[1]["ex"] == 3600  # TTL


# ── Search ─────────────────────────────────────────────────────────


class TestSearchAdapter:
    @pytest.mark.asyncio
    async def test_search_returns_candidates(self, settings: Settings) -> None:
        async def mock_search(**kwargs: Any) -> Any:
            doc1 = {
                "id": "c1",
                "job_id": "j1",
                "candidate_id": "c1",
                "score": 85,
                "@search.score": 0.92,
            }
            for doc in [doc1]:
                yield doc

        mock_client = MagicMock()
        mock_client.search = mock_search

        adapter = SearchAdapter(settings)
        output = await adapter.search_similar_candidates(
            SearchSimilarCandidatesInput(resume_embedding_ref="ref1", top_k=3),
            resume_embedding=[0.1] * 1536,
            client=mock_client,
        )

        assert isinstance(output, SearchSimilarCandidatesOutput)
        assert len(output.similar_candidates) == 1
        assert output.similar_candidates[0].candidate_id == "c1"
        assert output.similar_candidates[0].similarity == 0.92


# ── Cosmos DB ──────────────────────────────────────────────────────


class TestCosmosAdapter:
    @pytest.mark.asyncio
    async def test_flag_for_human_review(self, settings: Settings) -> None:
        mock_container = AsyncMock()
        mock_container.upsert_item = AsyncMock()

        adapter = CosmosAdapter(settings)
        output = await adapter.flag_for_human_review(
            FlagForHumanReviewInput(
                job_id="j1",
                reason="Low score",
                severity="high",
            ),
            client=mock_container,
        )

        assert isinstance(output, FlagForHumanReviewOutput)
        assert output.flagged is True
        assert output.review_id

    @pytest.mark.asyncio
    async def test_get_job_found(self, settings: Settings) -> None:
        mock_container = AsyncMock()
        mock_container.read_item.return_value = {
            "id": "j1",
            "status": "queued",
            "filename": "resume.pdf",
            "blob_path": "resumes-raw/j1/resume.pdf",
            "job_description": "dev",
            "uploaded_by": "user@test.com",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "retention_hold": False,
        }

        adapter = CosmosAdapter(settings)
        job = await adapter.get_job("j1", client=mock_container)

        assert job is not None
        assert job.id == "j1"
        assert job.status.value == "queued"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, settings: Settings) -> None:
        mock_container = AsyncMock()
        mock_container.read_item.side_effect = Exception("not found")

        adapter = CosmosAdapter(settings)
        job = await adapter.get_job("missing", client=mock_container)
        assert job is None


# ── Blob Storage ───────────────────────────────────────────────────


class TestBlobStorageAdapter:
    @pytest.mark.asyncio
    async def test_upload_resume(self, settings: Settings) -> None:
        mock_container = AsyncMock()

        adapter = BlobStorageAdapter(settings)
        path = await adapter.upload_resume(
            job_id="j1",
            safe_filename="resume.pdf",
            data=b"%PDF-1.4 fake",
            client=mock_container,
        )

        assert path == "resumes-raw/j1/resume.pdf"
        mock_container.upload_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_resume(self, settings: Settings) -> None:
        stream = AsyncMock()
        stream.readall.return_value = b"%PDF-1.4 content"

        mock_blob_client = AsyncMock()
        mock_blob_client.download_blob.return_value = stream

        # get_blob_client is sync, upload_blob is async — mix MagicMock base
        mock_container = MagicMock()
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.upload_blob = AsyncMock()

        adapter = BlobStorageAdapter(settings)
        data = await adapter.download_resume(
            "resumes-raw/j1/resume.pdf",
            client=mock_container,
        )

        assert data == b"%PDF-1.4 content"

    @pytest.mark.asyncio
    async def test_upload_report(self, settings: Settings) -> None:
        mock_container = AsyncMock()

        adapter = BlobStorageAdapter(settings)
        path = await adapter.upload_report(
            job_id="j1",
            report_json='{"score": 85}',
            client=mock_container,
        )

        assert path == "reports/j1/report.json"
