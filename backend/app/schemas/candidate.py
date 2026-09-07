"""
Candidate matching schemas for FactLens.
Represents paired facts identified as candidates for relationship reasoning.
"""

from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class CandidatePair(BaseModel):
    """A pair of facts deemed candidate for relationship reasoning (Corroboration/Contradiction/Context)."""

    fact_a_id: UUID
    fact_b_id: UUID
    similarity_score: float = Field(ge=0.0, le=1.0, description="Cosine or hybrid similarity between facts")
    subject_match: bool = Field(default=False, description="Whether entities or subjects match or align")
    predicate_match: bool = Field(default=False, description="Whether metrics or predicates align")
    temporal_overlap: bool = Field(default=False, description="Whether reporting periods overlap or coincide")
    metric_compatible: bool = Field(default=False, description="Whether units/metrics can be compared")
    match_reasons: list[str] = Field(default_factory=list, description="Explanations for why this pair was matched")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Auxiliary debugging or provenance context")


class CandidateSearchRequest(BaseModel):
    """Parameters for finding candidate facts for a query fact."""

    dataset_id: UUID
    query_fact_id: UUID | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.5, ge=0.0, le=1.0)
    cross_document_only: bool = Field(default=True, description="Only match facts from different documents")


class CandidateSearchResponse(BaseModel):
    """Response containing retrieved candidate pairs."""

    dataset_id: UUID
    total_candidates: int
    candidates: list[CandidatePair]
