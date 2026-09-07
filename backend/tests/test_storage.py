"""
Unit tests for Supabase Storage client.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock
from backend.app.config import Settings
from backend.app.storage.supabase_storage import SupabaseStorageClient


def test_canonical_path_structure():
    """Verify storage path matches documents/{dataset_id}/{document_id}/{filename}."""
    path = SupabaseStorageClient.get_canonical_path(
        dataset_id="ds-123",
        document_id="doc-456",
        filename="report.pdf",
    )
    assert path == "ds-123/doc-456/report.pdf"


@pytest.mark.asyncio
async def test_storage_upload_mocked():
    """Verify SupabaseStorageClient issues correct HTTP POST with upsert header."""
    settings = Settings(
        supabase_url="https://fake-project.supabase.co",
        supabase_service_role_key="fake-service-role-key",
        supabase_storage_bucket="documents",
        groq_api_key="gsk_key",
        jina_api_key="jina_key",
    )
    client = SupabaseStorageClient(settings)

    mock_resp = httpx.Response(
        status_code=200,
        json={"Key": "documents/ds-1/doc-1/test.pdf"},
        request=httpx.Request("POST", "https://fake-project.supabase.co"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await client.upload_file(b"%PDF-test", "ds-1/doc-1/test.pdf")

        assert result == "documents/ds-1/doc-1/test.pdf"
        assert mock_post.called
        headers = mock_post.call_args[1]["headers"]
        assert headers["x-upsert"] == "true"
        assert headers["Authorization"] == "Bearer fake-service-role-key"
