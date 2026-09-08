"""
Datasets API router for managing datasets.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.config import Settings, get_settings
from backend.app.database import get_all_datasets, get_dataset_by_id
from backend.app.schemas.api import DatasetCreateRequest, DatasetResponse
from backend.app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("", response_model=list[DatasetResponse])
def list_datasets(settings: Settings = Depends(get_settings)) -> list[DatasetResponse]:
    """List all registered datasets with document, fact, and relationship counts."""
    return get_all_datasets(settings)


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreateRequest,
    settings: Settings = Depends(get_settings),
) -> DatasetResponse:
    """Create a new dataset or retrieve existing dataset with the same name."""
    service = IngestionService(settings=settings)
    dataset_id = service.get_or_create_dataset(name=payload.name, description=payload.description)
    dataset = get_dataset_by_id(dataset_id, settings)
    if not dataset:
        raise HTTPException(status_code=500, detail="Failed to retrieve created dataset.")
    return dataset


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID,
    settings: Settings = Depends(get_settings),
) -> DatasetResponse:
    """Get metadata and counts for a specific dataset."""
    dataset = get_dataset_by_id(str(dataset_id), settings)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset_endpoint(
    dataset_id: UUID,
    settings: Settings = Depends(get_settings),
) -> None:
    """Delete a dataset and cascade its associated items."""
    from backend.app.database import delete_dataset
    success = delete_dataset(str(dataset_id), settings)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
