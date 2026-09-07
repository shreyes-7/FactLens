"""
FactLens Pydantic Schemas.
Domain models for chunks, facts, evidence, and structured LLM extraction.
"""

from backend.app.schemas.candidate import CandidatePair, CandidateSearchRequest, CandidateSearchResponse
from backend.app.schemas.chunk import ChunkCreate, ChunkResponse
from backend.app.schemas.evidence import EvidenceCreate, EvidenceResponse
from backend.app.schemas.fact import FactCreate, FactResponse, FactType
from backend.app.schemas.llm_extraction import ExtractedFactItem, FactExtractionBatch
from backend.app.schemas.relationship import (
    FactRelationshipBase,
    FactRelationshipCreate,
    FactRelationshipResponse,
    LLMReasoningOutput,
    RelationshipType,
)

__all__ = [
    "CandidatePair",
    "CandidateSearchRequest",
    "CandidateSearchResponse",
    "ChunkCreate",
    "ChunkResponse",
    "EvidenceCreate",
    "EvidenceResponse",
    "FactCreate",
    "FactResponse",
    "FactType",
    "ExtractedFactItem",
    "FactExtractionBatch",
    "FactRelationshipBase",
    "FactRelationshipCreate",
    "FactRelationshipResponse",
    "LLMReasoningOutput",
    "RelationshipType",
]

