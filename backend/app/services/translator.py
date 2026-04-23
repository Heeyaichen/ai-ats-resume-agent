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
    """Wraps Azure AI Translator for language detection and translation.

    Uses the Translator REST API via httpx since azure-ai-translation-document
    is for document translation, not text detection/translation.
    """

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
        import httpx

        sample = input_data.text[:_DETECTION_CHAR_LIMIT]
        logger.info("Detecting language (sample length=%d)", len(sample))

        url = f"{self._endpoint.rstrip('/')}/detect?api-version=3.0"
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": "application/json",
        }
        if self._region:
            headers["Ocp-Apim-Subscription-Region"] = self._region

        async with httpx.AsyncClient() as http:
            resp = await http.post(url, headers=headers, json=[{"text": sample}])
            resp.raise_for_status()
            detections = resp.json()

        detection = detections[0] if detections else {}
        code = detection.get("language", "en")

        # Map common codes to names.
        _names = {"en": "English", "fr": "French", "de": "German", "es": "Spanish",
                   "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
                   "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic"}

        return DetectLanguageOutput(
            language_code=code,
            language_name=_names.get(code, code),
            confidence=float(detection.get("score", 1.0)),
        )

    async def translate_text(
        self,
        input_data: TranslateTextInput,
        *,
        client: Any | None = None,
    ) -> TranslateTextOutput:
        """Translate text to English using Azure Translator."""
        import httpx

        logger.info("Translating from %s to en", input_data.source_language)

        url = f"{self._endpoint.rstrip('/')}/translate?api-version=3.0&from={input_data.source_language}&to=en"
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": "application/json",
        }
        if self._region:
            headers["Ocp-Apim-Subscription-Region"] = self._region

        async with httpx.AsyncClient() as http:
            resp = await http.post(url, headers=headers, json=[{"text": input_data.text}])
            resp.raise_for_status()
            translations = resp.json()

        translated = translations[0]["translations"][0]["text"] if translations else input_data.text

        return TranslateTextOutput(
            translated_text=translated,
            source_language=input_data.source_language,
        )
