"""
Facts API router for browsing, filtering, and inspecting grounded facts.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.config import Settings, get_settings
from backend.app.database import get_fact_detail, get_facts_with_evidence
from backend.app.schemas.api import FactsListResponse, FactWithEvidenceResponse, FactConfidenceResponse
from backend.app.services.confidence_service import FactConfidenceService

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
    Every fact includes source document filename, page numbers, exact grounded quotes,
    and deterministic confidence scores.
    """
    ds_id = str(dataset_id) if dataset_id else None
    doc_id = str(document_id) if document_id else None

    total, raw_facts = get_facts_with_evidence(
        dataset_id=ds_id,
        document_id=doc_id,
        category=category,
        entity=entity,
        search=search,
        limit=limit,
        offset=offset,
        settings=settings,
    )

    # Deterministically calculate confidence for each fact
    enriched_facts = []
    for f in raw_facts:
        f_dict = f.model_dump() if hasattr(f, "model_dump") else dict(f)
        ev = f_dict.get("evidence", [{}])[0] if f_dict.get("evidence") else None
        conf = FactConfidenceService.calculate_confidence(f_dict, ev)
        f_dict["confidence"] = conf.score
        f_dict["confidence_level"] = conf.level
        enriched_facts.append(FactWithEvidenceResponse(**f_dict))

    return FactsListResponse(
        total=total,
        limit=limit,
        offset=offset,
        facts=enriched_facts,
    )


@router.get("/{fact_id}", response_model=FactWithEvidenceResponse)
def get_fact(
    fact_id: UUID,
    settings: Settings = Depends(get_settings),
) -> FactWithEvidenceResponse:
    """Retrieve full detail for a single fact including all evidence grounding items and confidence."""
    fact = get_fact_detail(str(fact_id), settings)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact '{fact_id}' not found.")
    
    f_dict = fact.model_dump() if hasattr(fact, "model_dump") else dict(fact)
    ev = f_dict.get("evidence", [{}])[0] if f_dict.get("evidence") else None
    conf = FactConfidenceService.calculate_confidence(f_dict, ev)
    f_dict["confidence"] = conf.score
    f_dict["confidence_level"] = conf.level
    return FactWithEvidenceResponse(**f_dict)


@router.get("/{fact_id}/confidence", response_model=FactConfidenceResponse)
def get_fact_confidence(
    fact_id: UUID,
    settings: Settings = Depends(get_settings),
) -> FactConfidenceResponse:
    """
    Get detailed deterministic confidence score and evidence quality breakdown for a fact.
    Explains exactly which positive signals and negative warning signals influenced the score.
    """
    fact = get_fact_detail(str(fact_id), settings)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact '{fact_id}' not found.")

    f_dict = fact.model_dump() if hasattr(fact, "model_dump") else dict(fact)
    ev = f_dict.get("evidence", [{}])[0] if f_dict.get("evidence") else None
    result = FactConfidenceService.calculate_confidence(f_dict, ev)

    return FactConfidenceResponse(
        fact_id=fact_id,
        score=result.score,
        level=result.level,
        level_label=result.level_label,
        signals=[s.model_dump() for s in result.signals],
        positive_count=result.positive_count,
        negative_count=result.negative_count,
    )
