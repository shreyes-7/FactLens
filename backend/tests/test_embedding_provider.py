"""
Unit tests for Embedding providers and factory.
"""

import sys
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from backend.app.config import Settings
from backend.app.providers.embeddings import (
    get_embedding_provider,
    JinaEmbeddingProvider,
    LocalEmbeddingProvider,
)


def test_factory_returns_jina_by_default():
    """Verify factory returns JinaEmbeddingProvider with 1024 dimension."""
    settings = Settings(
        embedding_provider="jina",
        jina_api_key="jina_test_key",
        embedding_model="jina-embeddings-v3",
        embedding_dimension=1024,
        groq_api_key="gsk_key",
    )
    provider = get_embedding_provider(settings)
    assert isinstance(provider, JinaEmbeddingProvider)
    assert provider.provider_name == "jina"
    assert provider.dimension == 1024
    assert provider.model_name == "jina-embeddings-v3"


def test_sentence_transformers_not_loaded_when_jina_selected():
    """Verify sentence-transformers / HuggingFace local models are NOT imported when Jina is used."""
    settings = Settings(
        embedding_provider="jina",
        jina_api_key="jina_test_key",
        embedding_dimension=1024,
        groq_api_key="gsk_key",
    )
    _ = get_embedding_provider(settings)
    assert "sentence_transformers" not in sys.modules


@pytest.mark.asyncio
async def test_jina_embed_documents_and_query_tasks():
    """Verify Jina provider uses retrieval.passage for documents and retrieval.query for query."""
    provider = JinaEmbeddingProvider(api_key="jina_mock_key", dimension=1024)

    mock_vec = [0.1] * 1024
    mock_response = httpx.Response(
        status_code=200,
        json={"data": [{"embedding": mock_vec}]},
        request=httpx.Request("POST", provider.API_URL),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Test document embedding
        doc_vecs = await provider.embed_documents(["Test document chunk"])
        assert len(doc_vecs) == 1
        assert len(doc_vecs[0]) == 1024
        doc_payload = mock_post.call_args[1]["json"]
        assert doc_payload["task"] == "retrieval.passage"
        assert doc_payload["dimensions"] == 1024

        # Test query embedding
        query_vec = await provider.embed_query("Test user query")
        assert len(query_vec) == 1024
        query_payload = mock_post.call_args[1]["json"]
        assert query_payload["task"] == "retrieval.query"
        assert query_payload["dimensions"] == 1024


def test_local_provider_dimension_and_lazy_import():
    """Verify LocalEmbeddingProvider has dimension=384 without immediately importing sentence_transformers."""
    provider = LocalEmbeddingProvider(model_name="BAAI/bge-small-en-v1.5", dimension=384)
    assert provider.provider_name == "local"
    assert provider.dimension == 384
    assert provider._model is None
