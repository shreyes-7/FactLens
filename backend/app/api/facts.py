"""
Facts API router for browsing, filtering, and inspecting grounded facts.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.config import Settings, get_settings
from backend.app.database import get_fact_detail, get_facts_with_evidence
from backend.app.schemas.api import FactsListResponse, FactWithEvidenceResponse

router = APIRouter(prefix="/facts", tags=["Facts"])


@router.get("", response_model=FactsListResponse)
def list_facts(
    dataset_id: UUID | None = None,
    document_id: UUID | None = None,
    category: str | None = None,
    entity: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> FactsListResponse:
    """
    List extracted facts with pagination, full-text search, and filtering.
    Every fact includes source document filename, page numbers, and exact grounded quotes.
    """
    ds_id = str(dataset_id) if dataset_id else None
    doc_id = str(document_id) if document_id else None

    total, facts = get_facts_with_evidence(
        dataset_id=ds_id,
        document_id=doc_id,
        category=category,
        entity=entity,
        search=search,
        limit=limit,
        offset=offset,
        settings=settings,
    )

    return FactsListResponse(
        total=total,
        limit=limit,
        offset=offset,
        facts=facts,
    )


@router.get("/{fact_id}", response_model=FactWithEvidenceResponse)
def get_fact(
    fact_id: UUID,
    settings: Settings = Depends(get_settings),
) -> FactWithEvidenceResponse:
    """Retrieve full detail for a single fact including all evidence grounding items."""
    fact = get_fact_detail(str(fact_id), settings)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact '{fact_id}' not found.")
    return fact
