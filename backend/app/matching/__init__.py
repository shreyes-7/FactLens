"""
FactLens Matching Module.
Exposes candidate retrieval, structured filters, and similarity calculation engines.
"""

from backend.app.matching.candidate_retrieval import CandidateRetriever
from backend.app.matching.filters import (
    check_cross_document,
    check_dataset_boundary,
    check_metric_compatibility,
    check_non_self,
    check_predicate_alignment,
    check_temporal_compatibility,
    is_candidate_pair,
)
from backend.app.matching.similarity import (
    compute_hybrid_similarity,
    cosine_similarity,
    token_jaccard_similarity,
)

__all__ = [
    "CandidateRetriever",
    "check_dataset_boundary",
    "check_non_self",
    "check_cross_document",
    "check_temporal_compatibility",
    "check_metric_compatibility",
    "check_predicate_alignment",
    "is_candidate_pair",
    "cosine_similarity",
    "token_jaccard_similarity",
    "compute_hybrid_similarity",
]
