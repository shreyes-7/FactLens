"""
Pydantic schemas for structured LLM extraction output.
"""

from pydantic import BaseModel, Field
from backend.app.schemas.fact import FactType


class ExtractedFactItem(BaseModel):
    subject: str = Field(description="The entity, company, nation, or topic (e.g., 'Delhivery', 'India', 'Express Parcel')")
    predicate: str = Field(description="The specific metric or attribute (e.g., 'Revenue from operations', 'GDP growth', 'EBITDA')")
    raw_claim: str = Field(description="The full atomic claim as stated in the text")
    
    value_text: str | None = Field(default=None, description="Textual representation of the value if non-numeric")
    raw_value_text: str | None = Field(default=None, description="Exact substring representation of the value from text, e.g. 'Rs. 127 Cr' or '6.5%'")
    value_numeric: float | None = Field(default=None, description="Extracted numerical scalar, e.g. 127.0 or 6.5")
    value_boolean: bool | None = Field(default=None, description="Boolean value if applicable")
    
    unit: str | None = Field(default=None, description="Unit of measurement, e.g., 'INR Crore', 'percent', 'million', 'days'")
    fact_type: FactType = Field(default=FactType.NUMERICAL, description="NUMERICAL or SEMANTIC")
    
    period_text: str | None = Field(default=None, description="Time period mentioned, e.g., 'FY24', 'Q3 FY24', '2024-25'")
    scope: str | None = Field(default=None, description="Scope such as 'consolidated', 'standalone', 'segment'")
    geography: str | None = Field(default=None, description="Geographic entity if relevant, e.g., 'India', 'Global'")
    segment: str | None = Field(default=None, description="Business segment, e.g., 'Express Parcel', 'Part Truckload (PTL)'")
    status: str | None = Field(default="actual", description="'actual', 'forecast', 'projection', 'target'")
    attribution: str | None = Field(default=None, description="Source or authority cited in text, e.g., 'OECD', 'Management'")
    
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence in the extraction accuracy")
    quote: str = Field(description="EXACT verbatim quote from the text that proves this claim. MUST be an exact substring.")


class FactExtractionBatch(BaseModel):
    facts: list[ExtractedFactItem] = Field(default_factory=list, description="List of extracted facts from the passage")
