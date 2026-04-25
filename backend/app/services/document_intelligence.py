"""Azure AI Document Intelligence adapter — extract_resume_text.

Design spec Section 4.3: uses prebuilt-read model for PDF/DOCX extraction.
Falls back to pypdf for PDFs when DI returns empty or very short text.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import ExtractResumeTextInput, ExtractResumeTextOutput

logger = logging.getLogger(__name__)

# Minimum text length to consider extraction successful.
_MIN_TEXT_LENGTH = 20


class DocumentIntelligenceAdapter:
    """Wraps Azure AI Document Intelligence for resume text extraction."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.document_intelligence_endpoint
        self._key = settings.document_intelligence_key

    async def extract_resume_text(
        self,
        input_data: ExtractResumeTextInput,
        *,
        blob_bytes: bytes | None = None,
        client: Any | None = None,
    ) -> ExtractResumeTextOutput:
        """Extract text from a resume PDF/DOCX.

        Args:
            input_data: Contains blob_path (for logging only).
            blob_bytes: Raw file bytes (provided by caller from Blob Storage).
            client: Optional pre-built DocumentIntelligenceClient for testing.

        Returns:
            Extracted text, page count, and confidence score.
        """
        if client is None:
            client = self._build_client()
        if blob_bytes is None:
            raise ValueError("blob_bytes is required — download from Blob Storage first")

        logger.info("Extracting text from %s", input_data.blob_path)

        poller = await client.begin_analyze_document(
            "prebuilt-read",
            blob_bytes,
            content_type="application/octet-stream",
        )
        result = await poller.result()

        full_text = str(result.content)
        page_count = len(result.pages) if hasattr(result, "pages") else 1

        # If DI returned usable text, return it.
        if full_text and len(full_text.strip()) >= _MIN_TEXT_LENGTH:
            return ExtractResumeTextOutput(
                text=full_text,
                page_count=page_count,
                confidence=0.95,
            )

        # DI returned empty or very short text — try local fallback.
        logger.warning(
            "Document Intelligence returned %d chars for %s, trying local fallback",
            len(full_text), input_data.blob_path,
        )
        fallback = _local_pdf_extract(blob_bytes, input_data.blob_path)
        if fallback is not None:
            return fallback

        # Both failed — return whatever DI gave (may be empty).
        return ExtractResumeTextOutput(
            text=full_text,
            page_count=page_count,
            confidence=0.3,
        )

    def _build_client(self) -> Any:
        from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        return DocumentIntelligenceClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(self._key),
        )


def _local_pdf_extract(blob_bytes: bytes, blob_path: str) -> ExtractResumeTextOutput | None:
    """Extract text from PDF bytes using pypdf as a local fallback."""
    try:
        import pypdf
    except ImportError:
        logger.debug("pypdf not available for fallback extraction")
        return None

    # Only attempt for PDF files.
    if not blob_path.lower().endswith(".pdf"):
        return None

    try:
        reader = pypdf.PdfReader(io.BytesIO(blob_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        full_text = "\n".join(pages)
        if len(full_text.strip()) < _MIN_TEXT_LENGTH:
            return None

        logger.info(
            "Local PDF fallback extracted %d chars from %s (%d pages)",
            len(full_text), blob_path, len(reader.pages),
        )
        return ExtractResumeTextOutput(
            text=full_text,
            page_count=len(reader.pages),
            confidence=0.7,  # Lower confidence for fallback extraction.
        )
    except Exception:
        logger.debug("Local PDF fallback failed for %s", blob_path, exc_info=True)
        return None
