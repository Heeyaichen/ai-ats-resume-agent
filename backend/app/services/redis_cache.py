"""Redis cache adapter — embedding and similarity caching.

Design spec Section 7.4:
  - Key format: embedding:{model}:{sha256(text)}
  - Key format: similarity:{model}:{sha256(jd)}:{sha256(resume)}
  - TTL: 1 hour
  - Cache values must not include raw text.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from backend.app.config import Settings

logger = logging.getLogger(__name__)


class RedisCacheAdapter:
    """Redis-backed cache for embeddings and similarity scores."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.redis_url
        self._ttl = settings.redis_embedding_ttl_seconds
        self._embedding_model = settings.embedding_model_deployment_name
        self._client: Any | None = None

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _embedding_key(self, text: str) -> str:
        return f"embedding:{self._embedding_model}:{self._hash(text)}"

    def _similarity_key(self, jd_text: str, resume_text: str) -> str:
        return (
            f"similarity:{self._embedding_model}"
            f":{self._hash(jd_text)}:{self._hash(resume_text)}"
        )

    async def get_embedding(self, text: str) -> list[float] | None:
        """Return cached embedding or None."""
        client = await self._get_client()
        key = self._embedding_key(text)
        raw = await client.get(key)
        if raw is None:
            return None
        logger.info("Embedding cache hit for key=%s", key[:40])
        return json.loads(raw)

    async def set_embedding(self, text: str, embedding: list[float]) -> None:
        """Cache an embedding vector."""
        client = await self._get_client()
        key = self._embedding_key(text)
        await client.set(key, json.dumps(embedding), ex=self._ttl)

    async def get_similarity(self, jd_text: str, resume_text: str) -> float | None:
        """Return cached similarity score or None."""
        client = await self._get_client()
        key = self._similarity_key(jd_text, resume_text)
        raw = await client.get(key)
        if raw is None:
            return None
        logger.info("Similarity cache hit for key=%s", key[:40])
        return float(raw)

    async def set_similarity(self, jd_text: str, resume_text: str, score: float) -> None:
        """Cache a similarity score."""
        client = await self._get_client()
        key = self._similarity_key(jd_text, resume_text)
        await client.set(key, str(score), ex=self._ttl)

    async def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self._url)
        return self._client
