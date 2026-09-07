"""
Embedding Provider Base Interface.
Decouples vector embedding generation from specific embedding backends.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for all FactLens embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider (e.g. 'jina', 'local')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Embedding model identifier."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality (e.g. 1024 for Jina v3)."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of document chunks.
        Must return list of vectors of length `self.dimension`.
        """
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single user query.
        Must return vector of length `self.dimension`.
        """
        pass
