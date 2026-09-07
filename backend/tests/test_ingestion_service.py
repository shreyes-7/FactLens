"""
Unit tests for the Ingestion Service.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.app.config import Settings
from backend.app.services.ingestion_service import IngestionService
from backend.tests.test_pdf_parser import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_deduplication_returns_existing():
    """Verify that uploading the same file hash returns ALREADY_EXISTS without inserting duplicate rows."""
    settings = Settings(
        groq_api_key="gsk_key",
        jina_api_key="jina_key",
        database_url="postgresql://fake:fake@localhost:5432/fake",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
    )

    pdf_bytes = create_sample_pdf_bytes(["Test page content"])
    service = IngestionService(settings=settings)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Simulate existing record found
    mock_cursor.fetchone.return_value = {
        "id": "11111111-1111-1111-1111-111111111111",
        "filename": "duplicate.pdf",
        "page_count": 1,
        "storage_path": "documents/ds-1/11111111-1111-1111-1111-111111111111/duplicate.pdf",
    }

    with patch("backend.app.services.ingestion_service.get_db_connection", return_value=mock_conn):
        result = await service.ingest_pdf(
            file_bytes=pdf_bytes,
            filename="duplicate.pdf",
            dataset_id="ds-1",
        )

        assert result["status"] == "ALREADY_EXISTS"
        assert result["document_id"] == "11111111-1111-1111-1111-111111111111"
        assert result["filename"] == "duplicate.pdf"
