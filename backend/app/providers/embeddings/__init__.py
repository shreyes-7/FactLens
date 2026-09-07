"""
Embedding Provider Factory.
Instantiates the configured embedding provider according to settings.
"""

from backend.app.config import Settings, get_settings
from backend.app.providers.embeddings.base import EmbeddingProvider
from backend.app.providers.embeddings.jina import JinaEmbeddingProvider
from backend.app.providers.embeddings.local import LocalEmbeddingProvider


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """
    Factory function returning the configured embedding provider.
    Defaults to Jina AI hosted embeddings (1024 dimensions).
    """
    cfg = settings or get_settings()

    if cfg.embedding_provider == "jina":
        if not cfg.jina_api_key:
            raise ValueError("Cannot initialize JinaEmbeddingProvider: missing JINA_API_KEY.")
        return JinaEmbeddingProvider(
            api_key=cfg.jina_api_key,
            model=cfg.embedding_model,
            dimension=cfg.embedding_dimension,
        )
    elif cfg.embedding_provider == "local":
        return LocalEmbeddingProvider(
            model_name=cfg.embedding_model,
            dimension=cfg.embedding_dimension,
        )
    else:
        raise ValueError(
            f"Unsupported embedding provider: '{cfg.embedding_provider}'. Supported: 'jina', 'local'."
        )


__all__ = [
    "EmbeddingProvider",
    "JinaEmbeddingProvider",
    "LocalEmbeddingProvider",
    "get_embedding_provider",
]
