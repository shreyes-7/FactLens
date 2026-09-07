"""
Local Embedding Provider Implementation (Optional Provider).
Preserved for offline/local development with BAAI/bge-small-en-v1.5 (384 dimensions).
Uses lazy loading to ensure sentence-transformers is never imported when Jina is selected.
"""

from backend.app.providers.embeddings.base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers (optional)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dimension: int = 384,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model = None

    def _get_model(self):
        """Lazy load sentence_transformers only when actually used."""
        if self._model is None:
            try:
                import importlib
                st = importlib.import_module("sentence_transformers")
                self._model = st.SentenceTransformer(self._model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers is required for LocalEmbeddingProvider. "
                    "Install it or use EMBEDDING_PROVIDER=jina."
                )
        return self._model


    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    async def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        vector = model.encode([text], normalize_embeddings=True)[0]
        return vector.tolist()
