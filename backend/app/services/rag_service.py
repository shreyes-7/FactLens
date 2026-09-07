"""
FactLens RAG Service.
Implements the retrieval-augmented generation pipeline using Jina embeddings and Groq LLM.
"""

from typing import Any
from backend.app.config import Settings, get_settings
from backend.app.providers.llm import LLMProvider, get_llm_provider
from backend.app.providers.embeddings import EmbeddingProvider, get_embedding_provider
from backend.app.database import search_similar_chunks


class RAGService:
    """End-to-end RAG pipeline execution service."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm_provider or get_llm_provider(self.settings)
        self.embeddings = embedding_provider or get_embedding_provider(self.settings)

    async def answer_query(
        self,
        query: str,
        dataset_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Execute RAG pipeline:
        1. User query -> Jina API -> 1024-d query vector
        2. Vector similarity search in Supabase pgvector
        3. Context construction
        4. Groq LLM prompt
        5. Grounded final answer with citations
        """
        # Step 1: Embed query using Jina
        query_vector = await self.embeddings.embed_query(query)

        # Step 2: Vector search in Supabase pgvector
        retrieved_chunks = search_similar_chunks(
            query_embedding=query_vector,
            top_k=top_k,
            dataset_id=dataset_id,
            settings=self.settings,
        )

        # Step 3: Context construction
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            distance = chunk.get("distance", 0.0)
            score = 1.0 - distance if distance is not None else 1.0
            context_parts.append(
                f"[Source {i}] (chunk_id: {chunk['id']}, similarity_score: {score:.3f})\n{chunk['text']}"
            )

        context_str = "\n\n".join(context_parts) if context_parts else "No relevant context found in database."

        # Step 4 & 5: LLM prompt & grounded generation
        system_prompt = (
            "You are FactLens, an evidence-grounded fact analysis system. "
            "Answer the user's question accurately using ONLY the provided sources. "
            "Cite each source by [Source X] and note any differences or uncertainties. "
            "Do not hallucinate facts."
        )
        prompt = (
            f"Context Sources:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            "Provide a comprehensive, evidence-grounded response."
        )

        answer = await self.llm.generate(prompt=prompt, system_prompt=system_prompt)

        return {
            "query": query,
            "answer": answer,
            "sources": retrieved_chunks,
            "llm_provider": self.llm.provider_name,
            "llm_model": self.llm.model_name,
            "embedding_provider": self.embeddings.provider_name,
            "embedding_model": self.embeddings.model_name,
            "embedding_dimension": self.embeddings.dimension,
        }
