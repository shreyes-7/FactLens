"""
Matching Service for FactLens.
Orchestrates embedding generation for facts and candidate retrieval.
"""

import logging
from typing import Any
from uuid import UUID

from backend.app.config import Settings, get_settings
from backend.app.database import get_facts_for_matching, update_fact_embedding
from backend.app.matching.candidate_retrieval import CandidateRetriever
from backend.app.providers.embeddings import get_embedding_provider
from backend.app.providers.embeddings.base import EmbeddingProvider
from backend.app.schemas.candidate import CandidatePair, CandidateSearchResponse

logger = logging.getLogger("factlens.services.matching")


class MatchingService:
    """High-level service coordinating fact embeddings and cross-document candidate discovery."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_provider = embedding_provider or get_embedding_provider(self.settings)
        self.retriever = CandidateRetriever(embedding_provider=self.embedding_provider)

    async def embed_unembedded_facts(self, dataset_id: str | None = None) -> int:
        """
        Scan database for facts lacking embeddings, generate 1024-d vectors via Jina AI,
        and update the facts in Supabase PostgreSQL.
        """
        all_facts = get_facts_for_matching(dataset_id=dataset_id, settings=self.settings)
        unembedded = [f for f in all_facts if not f.get("embedding")]

        if not unembedded:
            logger.info("All facts already have embeddings.")
            return 0

        logger.info(f"Generating embeddings for {len(unembedded)} facts...")
        vectors = await self.retriever.generate_embeddings_for_facts(unembedded)

        updated_count = 0
        for fact_dict, vec in zip(unembedded, vectors):
            update_fact_embedding(
                fact_id=str(fact_dict["id"]),
                embedding=vec,
                settings=self.settings,
            )
            updated_count += 1

        logger.info(f"Successfully embedded and updated {updated_count} facts in database.")
        return updated_count

    async def discover_candidates_in_dataset(
        self,
        dataset_id: str,
        min_similarity: float = 0.5,
        require_cross_document: bool = True,
    ) -> CandidateSearchResponse:
        """
        Ensure facts are embedded, retrieve facts, and perform candidate discovery.
        Returns ranked CandidateSearchResponse.
        """
        # 1. Ensure all facts are embedded
        await self.embed_unembedded_facts(dataset_id=dataset_id)

        # 2. Retrieve all facts with embeddings
        facts = get_facts_for_matching(dataset_id=dataset_id, settings=self.settings)

        # 3. Find candidate pairs
        pairs = self.retriever.find_all_candidate_pairs(
            facts=facts,
            min_similarity=min_similarity,
            require_cross_document=require_cross_document,
        )

        return CandidateSearchResponse(
            dataset_id=UUID(dataset_id),
            total_candidates=len(pairs),
            candidates=pairs,
        )
