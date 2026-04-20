"""Azure AI Language adapter — PII detection and redaction.

Design spec Section 4.3: PII redaction uses Azure AI Language (NOT Content Safety).
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import CheckPIIAndSafetyInput, CheckPIIAndSafetyOutput

logger = logging.getLogger(__name__)


class LanguageAdapter:
    """Wraps Azure AI Language for PII recognition and redaction."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.language_endpoint
        self._key = settings.language_key

    async def recognize_pii(
        self,
        input_data: CheckPIIAndSafetyInput,
        *,
        client: Any | None = None,
    ) -> CheckPIIAndSafetyOutput:
        """Detect and redact PII from text. Returns sanitized text.

        Safety flagging is handled by ContentSafetyAdapter — this adapter
        only handles PII, but the output model is shared because the agent
        calls check_pii_and_safety as one combined tool.
        """
        if client is None:
            client = self._build_client()

        logger.info("Running PII recognition")

        response = await client.recognize_pii_entities(
            [input_data.text],
            language="en",
        )

        pii_categories: list[str] = []
        sanitized_text = input_data.text
        pii_detected = False

        # Response is a list of results — take the first one.
        result = response[0] if response else None
        if result is not None and hasattr(result, "entities") and result.entities:
            pii_detected = True
            for entity in result.entities:
                pii_categories.append(entity.category)
            if hasattr(result, "redacted_text"):
                sanitized_text = result.redacted_text

        return CheckPIIAndSafetyOutput(
            sanitized_text=sanitized_text,
            pii_detected=pii_detected,
            pii_categories=pii_categories,
            safety_flagged=False,
            safety_categories=[],
        )

    def _build_client(self) -> Any:
        from azure.ai.textanalytics.aio import TextAnalyticsClient
        from azure.core.credentials import AzureKeyCredential

        return TextAnalyticsClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(self._key),
        )
