"""
Jina AI Embedding Provider Implementation.
Primary and default embedding provider using Jina's hosted API (jina-embeddings-v3).
Produces 1024-dimensional vectors for both document chunks and user queries.
"""

import asyncio
import logging
from typing import Any
import httpx

from backend.app.providers.embeddings.base import EmbeddingProvider

logger = logging.getLogger("factlens.embeddings.jina")


class JinaEmbeddingProvider(EmbeddingProvider):
    """Hosted Jina Embeddings API client."""

    API_URL = "https://api.jina.ai/v1/embeddings"

    def __init__(
        self,
        api_key: str,
        model: str = "jina-embeddings-v3",
        dimension: int = 1024,
        timeout: float = 90.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Jina API key cannot be empty.")
        if dimension != 1024:
            raise ValueError(f"Jina embeddings v3 requires dimension=1024 (got {dimension}).")

        self._api_key = api_key.strip()
        self._model = model
        self._dimension = dimension
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "jina"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def _embed_batch(self, texts: list[str], task: str) -> list[list[float]]:
        """Call Jina API to embed a batch of texts with retry and backoff."""
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
            "dimensions": self._dimension,
            "task": task,
        }

        max_retries = 3
        backoff = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self.API_URL, headers=headers, json=payload)
                    if response.status_code == 429:
                        logger.warning(
                            f"Jina API 429 rate limit hit. Backing off for {backoff:.1f}s (attempt {attempt}/{max_retries})..."
                        )
                        if attempt == max_retries:
                            raise RuntimeError(f"Jina API rate limit exceeded after {max_retries} attempts.")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue

                    if response.status_code != 200:
                        error_preview = response.text[:200]
                        raise RuntimeError(f"Jina API error ({response.status_code}): {error_preview}")

                    data = response.json()
                    results = [item["embedding"] for item in data.get("data", [])]

                    # Strict dimension verification
                    for vec in results:
                        if len(vec) != self._dimension:
                            raise ValueError(
                                f"Dimension mismatch from Jina API: expected {self._dimension}, got {len(vec)}."
                            )

                    return results
            except httpx.RequestError as exc:
                logger.warning(
                    f"Jina API network error ({exc.__class__.__name__}). Retrying in {backoff:.1f}s (attempt {attempt}/{max_retries})..."
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Network error communicating with Jina API: {exc.__class__.__name__}"
                    ) from None
                await asyncio.sleep(backoff)
                backoff *= 2

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed document chunks using 'retrieval.passage' task.
        Guarantees 1024-dimensional vectors.
        """
        return await self._embed_batch(texts=texts, task="retrieval.passage")

    async def embed_query(self, text: str) -> list[float]:
        """
        Embed a search query using 'retrieval.query' task.
        Guarantees 1024-dimensional vector.
        """
        embeddings = await self._embed_batch(texts=[text], task="retrieval.query")
        if not embeddings:
            raise RuntimeError("Jina API returned empty embeddings for query.")
        return embeddings[0]
