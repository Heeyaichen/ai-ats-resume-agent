"""Combined PII + Safety service — check_pii_and_safety tool.

Design spec Section 4.3: check_pii_and_safety is a single tool that
calls both Azure AI Language (PII) and Azure AI Content Safety (moderation).
"""

from __future__ import annotations

from backend.app.config import Settings
from backend.app.models.tools import CheckPIIAndSafetyInput, CheckPIIAndSafetyOutput
from backend.app.services.language import LanguageAdapter
from backend.app.services.content_safety import ContentSafetyAdapter


class PIISafetyService:
    """Orchestrates PII redaction and content safety analysis."""

    def __init__(self, settings: Settings) -> None:
        self._language = LanguageAdapter(settings)
        self._safety = ContentSafetyAdapter(settings)

    async def check(
        self,
        input_data: CheckPIIAndSafetyInput,
        *,
        language_client: object | None = None,
        safety_client: object | None = None,
    ) -> CheckPIIAndSafetyOutput:
        """Run PII redaction first, then safety analysis on sanitized text."""
        pii_result = await self._language.recognize_pii(
            input_data, client=language_client,
        )
        safety_result = await self._safety.analyze_text(
            pii_result.sanitized_text, client=safety_client,
        )
        # Merge: sanitized text from PII, safety flags from Content Safety.
        return CheckPIIAndSafetyOutput(
            sanitized_text=pii_result.sanitized_text,
            pii_detected=pii_result.pii_detected,
            pii_categories=pii_result.pii_categories,
            safety_flagged=safety_result.safety_flagged,
            safety_categories=safety_result.safety_categories,
        )
