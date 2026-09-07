"""
FastAPI Request and Response Models for FactLens.
Provides strongly-typed schemas for health checks, dataset management,
document uploads, fact queries with grounded evidence, relationships, and the four assignment cases.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

from backend.app.schemas.relationship import RelationshipType


class HealthResponse(BaseModel):
    """System health check and diagnostic status."""
    status: str = Field(..., description="Overall system health status, e.g. 'ok' or 'degraded'")
    database_connected: bool = Field(..., description="Whether PostgreSQL connection succeeded")
    llm_provider: str = Field(..., description="Primary active LLM provider name")
    llm_model: str = Field(..., description="Active LLM model name")
    fallback_enabled: bool = Field(..., description="Whether secondary LLM fallback is active")
    embedding_provider: str = Field(..., description="Active embedding provider name")
    version: str = Field("0.1.0", description="FactLens API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DatasetResponse(BaseModel):
    """Dataset metadata and entity counts."""
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime | None = None
    document_count: int = 0
    fact_count: int = 0
    relationship_count: int = 0


class DatasetCreateRequest(BaseModel):
    """Payload to create or register a dataset."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class DocumentResponse(BaseModel):
    """Document summary record."""
    id: UUID
    dataset_id: UUID
    filename: str
    page_count: int = 0
    file_size_bytes: int = 0
    storage_path: str
    status: str = "ingested"
    created_at: datetime | None = None


class DocumentDetailResponse(DocumentResponse):
    """Detailed document record including processing run metrics."""
    total_facts_extracted: int = 0
    total_chunks: int = 0
    processing_runs: list[dict[str, Any]] = []


class DocumentUploadResponse(BaseModel):
    """Response returned upon successful PDF upload and ingestion."""
    document: DocumentResponse
    pages_extracted: int
    is_duplicate: bool = False
    message: str


class ProcessingRequest(BaseModel):
    """Options for document processing."""
    max_pages: int | None = Field(None, ge=1, description="Max pages to process. Null = all.")
    page_offset: int = Field(0, ge=0, description="Starting page index.")
    chunk_size: int = Field(800, ge=200, le=2000)
    chunk_overlap: int = Field(100, ge=0, le=500)


class ProcessingResponse(BaseModel):
    """Result of document fact extraction and chunking pipeline."""
    document_id: UUID
    status: str
    chunks_created: int
    facts_extracted: int
    facts_rejected: int
    message: str


class EvidenceItem(BaseModel):
    """Grounding evidence snippet."""
    id: UUID
    quote: str
    page_number: int
    printed_page_number: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    similarity_score: float | None = None


class FactWithEvidenceResponse(BaseModel):
    """Fact record bundled with its exact grounding evidence citations."""
    id: UUID
    document_id: UUID
    document_filename: str | None = None
    page_number: int | None = None
    printed_page_number: str | None = None
    entity: str
    category: str
    predicate: str
    raw_value: str
    normalized_value: float | None = None
    unit: str | None = None
    time_period: str | None = None
    scope: str | None = None
    status: str | None = None
    quote: str | None = None
    confidence_score: float | None = 1.0
    evidence: list[EvidenceItem] = []
    created_at: datetime | None = None


class FactsListResponse(BaseModel):
    """Paginated collection of facts."""
    total: int
    limit: int
    offset: int
    facts: list[FactWithEvidenceResponse]


class FactSummary(BaseModel):
    """Compact summary of a fact for relationship presentation."""
    id: UUID
    document_filename: str | None = None
    page_number: int | None = None
    entity: str
    predicate: str
    raw_value: str
    normalized_value: float | None = None
    unit: str | None = None
    time_period: str | None = None
    scope: str | None = None
    status: str | None = None
    quote: str | None = None


class RelationshipWithDetailsResponse(BaseModel):
    """Cross-document relationship between two facts with dual evidence and reasoning."""
    id: UUID
    fact_a_id: UUID
    fact_b_id: UUID
    fact_a: FactSummary
    fact_b: FactSummary
    relationship_type: RelationshipType
    confidence: float
    rationale: str
    contextual_factors: dict[str, Any] = {}
    evidence_a_quote: str | None = None
    evidence_b_quote: str | None = None
    created_at: datetime | None = None


class RelationshipsListResponse(BaseModel):
    """List of classified cross-document relationships."""
    total: int
    relationships: list[RelationshipWithDetailsResponse]


class CaseDemonstration(BaseModel):
    """Single assignment case demonstration with facts, evidence, and explanation."""
    case_number: int
    case_title: str
    case_type: str
    description: str
    fact_a: FactSummary
    fact_b: FactSummary | None = None
    evidence_a: str | None = None
    evidence_b: str | None = None
    system_reasoning: str
    contextual_factors: dict[str, Any] = {}


class FourCasesResponse(BaseModel):
    """Structured presentation of the four core assignment required cases."""
    title: str = "FactLens Core Assignment Evaluation Cases"
    dataset_name: str
    cases: list[CaseDemonstration]
