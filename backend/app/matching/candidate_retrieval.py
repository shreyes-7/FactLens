"""
Candidate Retrieval Engine for FactLens.
Orchestrates vector embedding generation, structured candidate filtering,
and hybrid similarity ranking to discover candidate fact pairs for relationship reasoning.
"""

import logging
from typing import Any
from uuid import UUID

from backend.app.matching.filters import (
    check_predicate_alignment,
    check_temporal_compatibility,
    is_candidate_pair,
)
from backend.app.matching.similarity import (
    compute_hybrid_similarity,
    cosine_similarity,
    token_jaccard_similarity,
)
from backend.app.providers.embeddings.base import EmbeddingProvider
from backend.app.schemas.candidate import CandidatePair

logger = logging.getLogger("factlens.matching.candidate_retrieval")


class CandidateRetriever:
    """Retrieval service to match candidate fact pairs within and across documents."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider

    @staticmethod
    def generate_fact_embedding_text(fact: dict[str, Any]) -> str:
        """
        Create a canonical textual representation of a fact for semantic embedding.
        Captures entity/subject, predicate/metric, raw claim, and reporting period.
        """
        subject = fact.get("subject", "").strip()
        predicate = fact.get("predicate", "").strip()
        claim = fact.get("raw_claim", "").strip()
        period = fact.get("period_text") or ""
        unit = fact.get("normalized_unit") or fact.get("unit") or ""

        parts = [f"Entity: {subject}", f"Metric: {predicate}", f"Claim: {claim}"]
        if period:
            parts.append(f"Period: {period}")
        if unit:
            parts.append(f"Unit: {unit}")

        return " | ".join(parts)

    async def generate_embeddings_for_facts(
        self, facts: list[dict[str, Any]]
    ) -> list[list[float]]:
        """Compute 1024-dimensional vectors for a list of facts using the configured embedding provider."""
        if not self.embedding_provider:
            raise ValueError("No embedding provider configured for CandidateRetriever.")

        texts = [self.generate_fact_embedding_text(f) for f in facts]
        return await self.embedding_provider.embed_documents(texts)

    @classmethod
    def find_candidates_for_fact(
        cls,
        query_fact: dict[str, Any],
        candidate_pool: list[dict[str, Any]],
        top_k: int = 10,
        min_similarity: float = 0.5,
        require_cross_document: bool = True,
    ) -> list[CandidatePair]:
        """
        Search a pool of facts for candidates matching a single query fact.
        Applies structured pre-filters and ranks candidates by hybrid similarity score.
        """
        candidates: list[CandidatePair] = []
        query_id = str(query_fact.get("id"))
        query_vec = query_fact.get("embedding")

        for candidate in candidate_pool:
            cand_id = str(candidate.get("id"))
            if query_id == cand_id:
                continue

            # 1. Structured filters
            eligible, filter_reasons = is_candidate_pair(
                query_fact, candidate, require_cross_document=require_cross_document
            )
            if not eligible:
                continue

            # 2. Vector & Hybrid similarity
            cand_vec = candidate.get("embedding")
            vec_sim = None
            if query_vec and cand_vec:
                vec_sim = cosine_similarity(query_vec, cand_vec)

            score = compute_hybrid_similarity(query_fact, candidate, vector_similarity=vec_sim)

            if score < min_similarity:
                continue

            # 3. Match signals
            temporal_ok, temporal_reason = check_temporal_compatibility(query_fact, candidate)
            pred_ok, _ = check_predicate_alignment(query_fact, candidate)
            subj_sim = token_jaccard_similarity(query_fact.get("subject"), candidate.get("subject"))

            reasons = list(filter_reasons)
            if vec_sim is not None:
                reasons.append(f"vector_sim_{vec_sim:.2f}")

            pair = CandidatePair(
                fact_a_id=UUID(query_id),
                fact_b_id=UUID(cand_id),
                similarity_score=score,
                subject_match=subj_sim >= 0.3,
                predicate_match=pred_ok,
                temporal_overlap=temporal_ok,
                metric_compatible=True,
                match_reasons=reasons,
                metadata={
                    "query_subject": query_fact.get("subject"),
                    "candidate_subject": candidate.get("subject"),
                    "query_predicate": query_fact.get("predicate"),
                    "candidate_predicate": candidate.get("predicate"),
                },
            )
            candidates.append(pair)

        # Sort descending by similarity score
        candidates.sort(key=lambda p: p.similarity_score, reverse=True)
        return candidates[:top_k]

    @classmethod
    def find_all_candidate_pairs(
        cls,
        facts: list[dict[str, Any]],
        min_similarity: float = 0.5,
        require_cross_document: bool = True,
    ) -> list[CandidatePair]:
        """
        Find all unique pairwise candidates in a set of facts.
        Enforces canonical ordering (fact_a_id < fact_b_id) to avoid duplicate reciprocal pairs.
        """
        unique_pairs: list[CandidatePair] = []
        n = len(facts)

        for i in range(n):
            fact_a = facts[i]
            id_a = str(fact_a.get("id"))
            vec_a = fact_a.get("embedding")

            for j in range(i + 1, n):
                fact_b = facts[j]
                id_b = str(fact_b.get("id"))
                vec_b = fact_b.get("embedding")

                # Ensure canonical uuid ordering: id_a < id_b
                first_fact, second_fact = (fact_a, fact_b) if id_a < id_b else (fact_b, fact_a)
                first_id, second_id = (id_a, id_b) if id_a < id_b else (id_b, id_a)
                first_vec, second_vec = (vec_a, vec_b) if id_a < id_b else (vec_b, vec_a)

                # 1. Structured filters
                eligible, filter_reasons = is_candidate_pair(
                    first_fact, second_fact, require_cross_document=require_cross_document
                )
                if not eligible:
                    continue

                # 2. Similarity calculation
                vec_sim = None
                if first_vec and second_vec:
                    vec_sim = cosine_similarity(first_vec, second_vec)

                score = compute_hybrid_similarity(first_fact, second_fact, vector_similarity=vec_sim)

                if score < min_similarity:
                    continue

                # 3. Match signals
                temporal_ok, _ = check_temporal_compatibility(first_fact, second_fact)
                pred_ok, _ = check_predicate_alignment(first_fact, second_fact)
                subj_sim = token_jaccard_similarity(first_fact.get("subject"), second_fact.get("subject"))

                reasons = list(filter_reasons)
                if vec_sim is not None:
                    reasons.append(f"vector_sim_{vec_sim:.2f}")

                pair = CandidatePair(
                    fact_a_id=UUID(first_id),
                    fact_b_id=UUID(second_id),
                    similarity_score=score,
                    subject_match=subj_sim >= 0.3,
                    predicate_match=pred_ok,
                    temporal_overlap=temporal_ok,
                    metric_compatible=True,
                    match_reasons=reasons,
                    metadata={
                        "fact_a_claim": first_fact.get("raw_claim"),
                        "fact_b_claim": second_fact.get("raw_claim"),
                        "fact_a_predicate": first_fact.get("predicate"),
                        "fact_b_predicate": second_fact.get("predicate"),
                    },
                )
                unique_pairs.append(pair)

        unique_pairs.sort(key=lambda p: p.similarity_score, reverse=True)
        return unique_pairs
