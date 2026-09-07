"""
Pydantic schemas for extracted facts.
Strictly mirrors the database constraints of the 'facts' table.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class FactType(str, Enum):
    NUMERICAL = "NUMERICAL"
    SEMANTIC = "SEMANTIC"
    DERIVED = "DERIVED"


class FactBase(BaseModel):
    subject: str = Field(min_length=1, description="Entity or concept the fact is about")
    predicate: str = Field(min_length=1, description="Attribute, metric, or relationship")
    raw_claim: str = Field(min_length=1, description="Original statement as extracted from text")
    
    value_text: str | None = None
    raw_value_text: str | None = None
    value_numeric: float | None = None
    normalized_value_numeric: float | None = None
    value_boolean: bool | None = None
    
    unit: str | None = None
    normalized_unit: str | None = None

    
    fact_type: FactType = FactType.NUMERICAL
    
    period_text: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    
    scope: str | None = None
    geography: str | None = None
    segment: str | None = None
    status: str | None = None
    attribution: str | None = None
    
    qualifiers: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fact_constraints(self) -> "FactBase":
        # At least one value field must be populated
        if self.value_text is None and self.value_numeric is None and self.value_boolean is None:
            raise ValueError("At least one of value_text, value_numeric, or value_boolean must be provided")
        
        # Period start <= period end if both present
        if self.period_start is not None and self.period_end is not None:
            if self.period_end < self.period_start:
                raise ValueError("period_end cannot be earlier than period_start")
        return self


class FactCreate(FactBase):
    id: UUID | None = None
    dataset_id: UUID
    document_id: UUID


class FactResponse(FactBase):
    id: UUID
    dataset_id: UUID
    document_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
