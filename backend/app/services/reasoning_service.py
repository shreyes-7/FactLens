"""
Reasoning Service for FactLens.
Coordinates candidate retrieval, evidence lookup, relationship classification, and persistence.
"""

import logging
from typing import Any
from uuid import UUID

from backend.app.config import Settings, get_settings
from backend.app.database import (
    get_all_facts,
    get_fact_evidence_quote,
    get_fact_relationships,
    insert_fact_relationship,
)
from backend.app.providers.llm import get_llm_provider
from backend.app.providers.llm.base import LLMProvider
from backend.app.reasoning.relationship_classifier import RelationshipClassifier
from backend.app.schemas.relationship import FactRelationshipCreate, FactRelationshipResponse
from backend.app.services.matching_service import MatchingService

logger = logging.getLogger("factlens.services.reasoning")


class ReasoningService:
    """Service orchestrating candidate pair reasoning and relationship persistence."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        matching_service: MatchingService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_provider = llm_provider or get_llm_provider(self.settings)
        self.matching_service = matching_service or MatchingService(settings=self.settings)
        self.classifier = RelationshipClassifier(llm_provider=self.llm_provider)

    async def reason_candidate_pairs_in_dataset(
        self,
        dataset_id: str,
        min_similarity: float = 0.45,
        require_cross_document: bool = False,
    ) -> list[FactRelationshipResponse]:
        """
        Discover candidate fact pairs, classify their relationships, and persist to database.
        """
        # 1. Discover candidate pairs
        logger.info(f"Discovering candidate pairs in dataset {dataset_id}...")
        match_response = await self.matching_service.discover_candidates_in_dataset(
            dataset_id=dataset_id,
            min_similarity=min_similarity,
            require_cross_document=require_cross_document,
        )

        if not match_response.candidates:
            logger.info("No candidate pairs met the matching criteria.")
            return []

        # 2. Fetch facts map for fast attribute lookup
        all_facts = get_all_facts(dataset_id=dataset_id, settings=self.settings)
        facts_by_id = {str(f["id"]): f for f in all_facts}

        classified_relationships: list[FactRelationshipResponse] = []

        # 3. Classify each pair
        for pair in match_response.candidates:
            id_a = str(pair.fact_a_id)
            id_b = str(pair.fact_b_id)

            fact_a = facts_by_id.get(id_a)
            fact_b = facts_by_id.get(id_b)

            if not fact_a or not fact_b:
                continue

            ev_a = get_fact_evidence_quote(id_a, settings=self.settings)
            ev_b = get_fact_evidence_quote(id_b, settings=self.settings)

            rel_create: FactRelationshipCreate = await self.classifier.classify_pair(
                fact_a=fact_a,
                fact_b=fact_b,
                evidence_a=ev_a,
                evidence_b=ev_b,
            )

            # Persist to database
            persisted_id = insert_fact_relationship(rel_create.model_dump(), settings=self.settings)

            resp = FactRelationshipResponse(
                id=UUID(persisted_id),
                fact_a_id=rel_create.fact_a_id,
                fact_b_id=rel_create.fact_b_id,
                relationship_type=rel_create.relationship_type,
                confidence=rel_create.confidence,
                reason=rel_create.reason,
                contextual_factors=rel_create.contextual_factors,
                reasoning_method=rel_create.reasoning_method,
                model=rel_create.model,
            )
            classified_relationships.append(resp)

        logger.info(f"Successfully reasoned and persisted {len(classified_relationships)} fact relationships.")
        return classified_relationships
