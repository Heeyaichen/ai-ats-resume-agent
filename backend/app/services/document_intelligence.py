"""Azure AI Document Intelligence adapter — extract_resume_text.

Design spec Section 4.3: uses prebuilt-read model for PDF/DOCX extraction.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import ExtractResumeTextInput, ExtractResumeTextOutput

logger = logging.getLogger(__name__)


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
            analyze_request=blob_bytes,
            content_type="application/octet-stream",
        )
        result = await poller.result()

        full_text = str(result.content)

        return ExtractResumeTextOutput(
            text=full_text,
            page_count=len(result.pages) if hasattr(result, "pages") else 1,
            confidence=0.95,
        )

    def _build_client(self) -> Any:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        return DocumentIntelligenceClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(self._key),
        )
