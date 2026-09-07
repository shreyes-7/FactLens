"""
Pydantic schemas for text chunks.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class ChunkBase(BaseModel):
    document_id: UUID
    page_id: UUID
    chunk_index: int = Field(ge=0, description="0-indexed position within page")
    text: str = Field(min_length=1, description="Chunk text content")
    start_offset: int | None = Field(default=None, ge=0, description="Char start in page")
    end_offset: int | None = Field(default=None, ge=0, description="Char end in page")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_offsets(self) -> "ChunkBase":
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset < self.start_offset:
                raise ValueError("end_offset cannot be less than start_offset")
        return self


class ChunkCreate(ChunkBase):
    id: UUID | None = None
    embedding: list[float] | None = None


class ChunkResponse(ChunkBase):
    id: UUID
    embedding: list[float] | None = None
    created_at: datetime | None = None
