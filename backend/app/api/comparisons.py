"""
Comparisons API router for 'What Changed?' Cross-Document Comparison.
Fast, deterministic multi-document comparison across 2 to 5 documents.
Zero LLM calls.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from backend.app.config import Settings, get_settings
from backend.app.schemas.api import DocumentComparisonResponse
from backend.app.services.comparison_service import DocumentComparisonService

router = APIRouter(prefix="/comparisons", tags=["Comparisons"])


@router.post("", response_model=DocumentComparisonResponse)
def compare_documents(
    payload: dict[str, list[str]] = Body(..., example={"document_ids": ["doc_1_uuid", "doc_2_uuid"]}),
    settings: Settings = Depends(get_settings),
) -> DocumentComparisonResponse:
    """
    Compare 2 to 5 documents to discover what metrics increased, decreased,
    stayed unchanged, were newly added, or changed context.
    """
    doc_ids = payload.get("document_ids", [])
    if not doc_ids or len(doc_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two document IDs must be provided for cross-document comparison."
        )

    svc = DocumentComparisonService(settings=settings)
    try:
        return svc.compare_documents(doc_ids)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("", response_model=DocumentComparisonResponse)
def compare_documents_get(
    document_ids: list[str] = Query(..., description="List of 2 to 5 document UUIDs to compare"),
    settings: Settings = Depends(get_settings),
) -> DocumentComparisonResponse:
    """
    GET version for quick URL sharing and browser testing.
    """
    if not document_ids or len(document_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two document IDs must be provided for cross-document comparison."
        )

    svc = DocumentComparisonService(settings=settings)
    try:
        return svc.compare_documents(document_ids)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
