"""Azure AI Search adapter — vector similarity search.

Design spec Section 7.5: candidate-embeddings index with 1536-dim vectors.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import Settings
from backend.app.models.tools import (
    SearchSimilarCandidatesInput,
    SearchSimilarCandidatesOutput,
    SimilarCandidateResult,
)

logger = logging.getLogger(__name__)


class SearchAdapter:
    """Wraps Azure AI Search for vector similarity queries."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.search_endpoint
        self._key = settings.search_key
        self._index_name = settings.search_index_name

    async def search_similar_candidates(
        self,
        input_data: SearchSimilarCandidatesInput,
        resume_embedding: list[float],
        *,
        client: Any | None = None,
    ) -> SearchSimilarCandidatesOutput:
        """Search for candidates with similar embeddings.

        Args:
            input_data: Contains resume_embedding_ref and top_k.
            resume_embedding: The actual embedding vector to search with.
            client: Optional pre-built SearchClient for testing.
        """
        if client is None:
            client = self._build_client()

        logger.info(
            "Searching similar candidates (top_k=%d, embedding_dim=%d)",
            input_data.top_k,
            len(resume_embedding),
        )

        results = client.search(
            search_text=None,
            vector=resume_embedding,
            vector_fields="embedding",
            top=input_data.top_k,
            select=["id", "job_id", "candidate_id", "score"],
        )

        candidates: list[SimilarCandidateResult] = []
        async for doc in results:
            candidates.append(
                SimilarCandidateResult(
                    candidate_id=doc.get("candidate_id", doc.get("id", "")),
                    job_id=doc.get("job_id", ""),
                    score=int(doc.get("score", 0)),
                    similarity=float(doc.get("@search.score", 0.0)),
                )
            )

        return SearchSimilarCandidatesOutput(similar_candidates=candidates)

    def _build_client(self) -> Any:
        from azure.search.documents.aio import SearchClient
        from azure.core.credentials import AzureKeyCredential

        return SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name,
            credential=AzureKeyCredential(self._key),
        )
