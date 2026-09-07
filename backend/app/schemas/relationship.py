"""
Pydantic schemas for Fact Relationships.
Matches the constraints of the 'fact_relationships' database table.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class RelationshipType(str, Enum):
    """Allowed fact relationship classifications as defined by ARCHITECT_RULES.md."""
    CORROBORATES = "CORROBORATES"
    CONTRADICTS = "CONTRADICTS"
    CONTEXTUAL_DIFFERENCE = "CONTEXTUAL_DIFFERENCE"
    RELATED = "RELATED"
    UNCERTAIN = "UNCERTAIN"


class FactRelationshipBase(BaseModel):
    """Base schema for a relationship between two facts."""

    fact_a_id: UUID
    fact_b_id: UUID
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="Confidence in the classification")
    reason: str = Field(min_length=1, description="Evidence-grounded rationale for the relationship")
    contextual_factors: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value context explaining difference (e.g. temporal, accounting, scope)",
    )
    reasoning_method: str | None = Field(default="hybrid", description="'deterministic', 'llm', or 'hybrid'")
    model: str | None = None
    prompt_version: str | None = None

    @model_validator(mode="after")
    def validate_canonical_ordering(self) -> "FactRelationshipBase":
        """Enforce strict database constraint: fact_a_id < fact_b_id."""
        if str(self.fact_a_id) >= str(self.fact_b_id):
            raise ValueError(
                f"fact_a_id ({self.fact_a_id}) must be strictly less than fact_b_id ({self.fact_b_id}) to prevent reciprocal duplicate rows."
            )
        return self


class FactRelationshipCreate(FactRelationshipBase):
    id: UUID | None = None


class FactRelationshipResponse(FactRelationshipBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LLMReasoningOutput(BaseModel):
    """Schema for structured LLM contextual reasoning output."""

    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reason: str = Field(min_length=1, description="Detailed explanation grounded in the facts and evidence")
    contextual_factors: dict[str, Any] = Field(
        default_factory=dict,
        description="Key differences identified: e.g. temporal_difference, accounting_methodology, scope_perimeter, status_vintage",
    )
