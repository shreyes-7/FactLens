"""
Documents API router for PDF uploads, ingestion, page inspection, and processing.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from backend.app.config import Settings, get_settings
from backend.app.database import get_all_documents, get_document_detail, reset_document_processing_status
from backend.app.schemas.api import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ProcessingRequest,
    ProcessingResponse,
)
from backend.app.security.file_validation import validate_pdf_file
from backend.app.services.ingestion_service import IngestionService
from backend.app.services.processing_service import ProcessingService

logger = logging.getLogger("factlens.api.documents")

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    dataset_id: UUID | None = None,
    settings: Settings = Depends(get_settings),
) -> list[DocumentResponse]:
    """List documents, optionally filtered by dataset ID."""
    d_id = str(dataset_id) if dataset_id else None
    return get_all_documents(dataset_id=d_id, settings=settings)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: UUID,
    settings: Settings = Depends(get_settings),
) -> DocumentDetailResponse:
    """Retrieve detailed document metadata, fact counts, and processing runs."""
    doc = get_document_detail(str(document_id), settings)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return doc


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF document file to upload and ingest"),
    dataset_id: str | None = Form(None, description="UUID of existing dataset"),
    dataset_name: str = Form("delhivery", description="Fallback dataset name if dataset_id not provided"),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadResponse:
    """
    Upload a PDF document:
    1. Uploads binary to Supabase Storage.
    2. Parses all pages, text, and layout.
    3. Persists document and page records to database.
    4. Handles file hash deduplication gracefully.
    """
    file_bytes = await file.read()
    sanitized_filename = validate_pdf_file(
        filename=file.filename or "document.pdf",
        file_bytes=file_bytes,
        max_file_size_mb=settings.max_file_size_mb,
    )

    ingestion_service = IngestionService(settings=settings)

    target_dataset_id = dataset_id
    if not target_dataset_id:
        target_dataset_id = ingestion_service.get_or_create_dataset(name=dataset_name)

    try:
        result = await ingestion_service.ingest_pdf(
            file_bytes=file_bytes,
            filename=sanitized_filename,
            dataset_id=target_dataset_id,
        )
    except Exception as e:
        logger.error(f"Error ingesting PDF '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    doc_data = result["document"]
    pages_count = result.get("pages_extracted", doc_data.get("page_count", 0))

    return DocumentUploadResponse(
        document=DocumentResponse(
            id=doc_data["id"],
            dataset_id=doc_data["dataset_id"],
            filename=doc_data["filename"],
            page_count=doc_data["page_count"],
            file_size_bytes=doc_data["file_size_bytes"],
            storage_path=doc_data["storage_path"],
            status=doc_data["status"],
            created_at=doc_data.get("created_at"),
        ),
        pages_extracted=pages_count,
        is_duplicate=result.get("is_duplicate", False),
        message=result.get("message", "Document successfully ingested."),
    )


async def _run_processing_task(
    doc_id: str,
    max_pages: int | None,
    page_offset: int,
    chunk_size: int,
    chunk_overlap: int,
    settings: Settings,
    force: bool = False,
):
    """Background task runner for document processing."""
    try:
        proc_service = ProcessingService(settings=settings)
        await proc_service.process_document(
            document_id=doc_id,
            max_pages=max_pages,
            page_offset=page_offset,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            force=force,
        )
    except Exception as e:
        logger.error(f"Background processing task failed for document {doc_id}: {e}", exc_info=True)


@router.post("/{document_id}/reset-processing")
def reset_document_processing(
    document_id: UUID,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Manually clear any active or stuck PROCESSING runs for this document,
    marking them as FAILED so the document can be immediately re-processed.
    """
    doc = get_document_detail(str(document_id), settings)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    was_reset = reset_document_processing_status(str(document_id), settings)
    return {
        "document_id": str(document_id),
        "reset": was_reset,
        "message": "Processing run status has been reset." if was_reset else "No active processing run found.",
    }


@router.post("/{document_id}/process", response_model=ProcessingResponse)
async def process_document(
    document_id: UUID,
    payload: ProcessingRequest = ProcessingRequest(),
    background: bool = Query(False, description="Whether to execute as a background task"),
    force: bool = Query(False, description="Whether to force execution and clear any stuck active runs"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    settings: Settings = Depends(get_settings),
) -> ProcessingResponse:
    """
    Trigger chunking, vector embedding, atomic fact extraction, and evidence grounding.
    Can be run synchronously (for small page subsets or immediate response) or in background.
    """
    doc = get_document_detail(str(document_id), settings)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if background:
        background_tasks.add_task(
            _run_processing_task,
            doc_id=str(document_id),
            max_pages=payload.max_pages,
            page_offset=payload.page_offset,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
            settings=settings,
            force=force,
        )
        return ProcessingResponse(
            document_id=document_id,
            status="processing_queued",
            chunks_created=0,
            facts_extracted=0,
            facts_rejected=0,
            message="Document processing queued in background.",
        )

    proc_service = ProcessingService(settings=settings)
    try:
        result = await proc_service.process_document(
            document_id=str(document_id),
            max_pages=payload.max_pages,
            page_offset=payload.page_offset,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
            force=force,
        )
        return ProcessingResponse(
            document_id=document_id,
            status=result.get("status", "completed"),
            chunks_created=result.get("chunks_created", 0),
            facts_extracted=result.get("facts_extracted", 0),
            facts_rejected=result.get("facts_rejected", 0),
            message="Document successfully processed.",
        )
    except Exception as e:
        logger.error(f"Processing error for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
