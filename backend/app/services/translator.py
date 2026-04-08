"""Azure AI Translator adapter — detect_language and translate_text.

Design spec Section 4.3: detect endpoint and translate endpoint with target `en`.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import (
    DetectLanguageInput,
    DetectLanguageOutput,
    TranslateTextInput,
    TranslateTextOutput,
)

logger = logging.getLogger(__name__)

_DETECTION_CHAR_LIMIT = 500


class TranslatorAdapter:
    """Wraps Azure AI Translator for language detection and translation."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.translator_endpoint
        self._key = settings.translator_key
        self._region = settings.translator_region

    async def detect_language(
        self,
        input_data: DetectLanguageInput,
        *,
        client: Any | None = None,
    ) -> DetectLanguageOutput:
        """Detect the language of the input text.

        Passes at most the first 500 safe characters per spec.
        """
        if client is None:
            client = self._build_client()

        sample = input_data.text[:_DETECTION_CHAR_LIMIT]
        logger.info("Detecting language (sample length=%d)", len(sample))

        response = await client.detect(sample)
        detection = response[0] if response else {}

        return DetectLanguageOutput(
            language_code=detection.get("language", "en"),
            language_name=detection.get("language", "English"),
            confidence=float(detection.get("score", 1.0)),
        )

    async def translate_text(
        self,
        input_data: TranslateTextInput,
        *,
        client: Any | None = None,
    ) -> TranslateTextOutput:
        """Translate text to English using Azure Translator."""
        if client is None:
            client = self._build_client()

        logger.info("Translating from %s to en", input_data.source_language)

        response = await client.translate(
            input_data.text,
            to_language="en",
            from_language=input_data.source_language,
        )
        translated = response[0]["translations"][0]["text"] if response else input_data.text

        return TranslateTextOutput(
            translated_text=translated,
            source_language=input_data.source_language,
        )

    def _build_client(self) -> Any:
        # The Translator REST API is used directly via httpx/Azure SDK.
        # For now, provide a thin wrapper; the exact client pattern depends
        # on the SDK version resolved at lock time.
        raise NotImplementedError(
            "Translator client construction — implement when Azure credentials are available"
        )
