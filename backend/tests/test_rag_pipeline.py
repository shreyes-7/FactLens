"""
Unit tests for the FactLens RAG pipeline service.
"""

import pytest
from unittest.mock import patch, AsyncMock
from backend.app.config import Settings
from backend.app.services.rag_service import RAGService
from backend.app.providers.llm.base import LLMProvider
from backend.app.providers.embeddings.base import EmbeddingProvider


class MockLLM(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return "openai/gpt-oss-120b"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"Mock answer generated based on: {prompt[:40]}..."

    async def extract_facts(self, text: str, context: dict | None = None):
        return []

    async def reason_relationship(self, fact_a, fact_b, evidence_a, evidence_b):
        return {}


class MockEmbeddings(EmbeddingProvider):
    @property
    def provider_name(self) -> str:
        return "jina"

    @property
    def model_name(self) -> str:
        return "jina-embeddings-v3"

    @property
    def dimension(self) -> int:
        return 1024

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.05] * 1024 for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.05] * 1024


@pytest.mark.asyncio
async def test_rag_pipeline_execution():
    """Verify RAGService orchestrates query embedding, vector search, context, and LLM."""
    settings = Settings(
        groq_api_key="gsk_mock",
        jina_api_key="jina_mock",
    )
    llm = MockLLM()
    embeddings = MockEmbeddings()

    rag = RAGService(llm_provider=llm, embedding_provider=embeddings, settings=settings)

    mock_retrieved_chunks = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "document_id": "22222222-2222-2222-2222-222222222222",
            "page_id": "33333333-3333-3333-3333-333333333333",
            "chunk_index": 0,
            "text": "Delhivery reported revenue of 8,142 Cr in FY24.",
            "distance": 0.12,
        }
    ]

    with patch("backend.app.services.rag_service.search_similar_chunks", return_value=mock_retrieved_chunks) as mock_search:
        result = await rag.answer_query("What was Delhivery's FY24 revenue?")

        assert mock_search.called
        assert result["llm_provider"] == "groq"
        assert result["llm_model"] == "openai/gpt-oss-120b"
        assert result["embedding_provider"] == "jina"
        assert result["embedding_dimension"] == 1024
        assert len(result["sources"]) == 1
        assert "Delhivery reported revenue" in result["sources"][0]["text"]
        assert "Mock answer" in result["answer"]
