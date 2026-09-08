"""
Relationships API router for cross-document fact comparison, corroboration, and contradiction analysis.
"""

import logging
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.config import Settings, get_settings
from backend.app.database import cleanup_same_page_relationships, get_relationships_detailed
from backend.app.schemas.api import RelationshipsListResponse, RelationshipWithDetailsResponse
from backend.app.schemas.relationship import RelationshipType
from backend.app.services.reasoning_service import ReasoningService

logger = logging.getLogger("factlens.api.relationships")

router = APIRouter(prefix="/relationships", tags=["Relationships"])


@router.get("", response_model=RelationshipsListResponse)
def list_relationships(
    dataset_id: UUID | None = None,
    type: RelationshipType | None = Query(None, description="Filter by relationship type (e.g. CORROBORATES, CONTRADICTS)"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    cross_document_only: bool = Query(False, description="Filter for cross-document comparisons only"),
    exclude_same_page: bool = Query(True, description="Exclude trivial same-page line item pairs"),
    settings: Settings = Depends(get_settings),
) -> RelationshipsListResponse:
    """
    List cross-document relationships between facts.
    Returns complete comparison cards with Fact A, Fact B, dual evidence quotes, and rationales.
    """
    ds_id = str(dataset_id) if dataset_id else None
    rel_type_str = type.value if type else None

    relationships = get_relationships_detailed(
        dataset_id=ds_id,
        relationship_type=rel_type_str,
        min_confidence=min_confidence,
        cross_document_only=cross_document_only,
        exclude_same_page=exclude_same_page,
        settings=settings,
    )

    return RelationshipsListResponse(
        total=len(relationships),
        relationships=relationships,
    )


@router.post("/cleanup-same-page")
def purge_same_page_relationships(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Purge trivial same-page line item relationships that clutter the cross-document view."""
    purged = cleanup_same_page_relationships(settings=settings)
    logger.info(f"Purged {purged} trivial same-page relationships from database.")
    return {"status": "ok", "purged_count": purged}



@router.post("/reason", response_model=RelationshipsListResponse)
async def trigger_relationship_reasoning(
    dataset_id: UUID,
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.65, ge=0.0, le=1.0),
    settings: Settings = Depends(get_settings),
) -> RelationshipsListResponse:
    """
    Execute candidate matching and hybrid relationship reasoning across all facts in a dataset.
    Discovered relationships are automatically classified and persisted to the database.
    """
    reasoning_service = ReasoningService(settings=settings)
    try:
        saved_rels = await reasoning_service.reason_dataset_relationships(
            dataset_id=str(dataset_id),
            top_k_candidates=top_k,
            min_similarity=min_similarity,
        )
        logger.info(f"Reasoning completed: {len(saved_rels)} relationships evaluated/saved.")
    except Exception as e:
        logger.error(f"Reasoning pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")

    # Return refreshed relationships
    relationships = get_relationships_detailed(
        dataset_id=str(dataset_id),
        settings=settings,
    )

    return RelationshipsListResponse(
        total=len(relationships),
        relationships=relationships,
    )
