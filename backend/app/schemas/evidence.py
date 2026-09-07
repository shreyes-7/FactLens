"""
Pydantic schemas for evidence grounding.
Mirrors database constraints of the 'evidence' table.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class EvidenceBase(BaseModel):
    quote: str = Field(min_length=1, description="Exact source passage/sentence quoted verbatim")
    start_offset: int | None = Field(default=None, ge=0, description="Char start in page text")
    end_offset: int | None = Field(default=None, ge=0, description="Char end in page text")
    extraction_method: str = Field(default="llm_structured_extraction")
    extraction_confidence: float | None = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceBase":
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset < self.start_offset:
                raise ValueError("end_offset cannot be less than start_offset")
        return self


class EvidenceCreate(EvidenceBase):
    id: UUID | None = None
    fact_id: UUID
    document_id: UUID
    page_id: UUID
    chunk_id: UUID | None = None


class EvidenceResponse(EvidenceBase):
    id: UUID
    fact_id: UUID
    document_id: UUID
    page_id: UUID
    chunk_id: UUID | None = None
    created_at: datetime | None = None
