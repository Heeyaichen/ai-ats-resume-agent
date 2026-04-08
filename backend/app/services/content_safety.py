"""Azure AI Content Safety adapter — harmful content moderation.

Design spec Section 4.3 / 2.5: Content Safety is for moderation ONLY.
PII detection uses Azure AI Language, not this service.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import CheckPIIAndSafetyOutput

logger = logging.getLogger(__name__)


class ContentSafetyAdapter:
    """Wraps Azure AI Content Safety for text moderation."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.content_safety_endpoint
        self._key = settings.content_safety_key

    async def analyze_text(
        self,
        text: str,
        *,
        client: Any | None = None,
    ) -> CheckPIIAndSafetyOutput:
        """Analyze text for harmful content.

        Returns only the safety fields; PII fields are always default.
        The caller (tool_executor) merges this with LanguageAdapter output.
        """
        if client is None:
            client = self._build_client()

        logger.info("Running content safety analysis")

        response = await client.analyze_text(text)

        safety_flagged = False
        safety_categories: list[str] = []

        if hasattr(response, "categories_analysis"):
            for analysis in response.categories_analysis:
                if analysis.severity > 0:
                    safety_flagged = True
                    safety_categories.append(analysis.category)

        return CheckPIIAndSafetyOutput(
            sanitized_text=text,
            pii_detected=False,
            pii_categories=[],
            safety_flagged=safety_flagged,
            safety_categories=safety_categories,
        )

    def _build_client(self) -> Any:
        from azure.ai.contentsafety import ContentSafetyClient
        from azure.core.credentials import AzureKeyCredential

        return ContentSafetyClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(self._key),
        )
