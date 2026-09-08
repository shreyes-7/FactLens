"""
Comprehensive Automated Tests for FactLens FastAPI Application.
Tests health, datasets, documents, facts with evidence, relationships, and four cases endpoints.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock
from backend.app.main import app


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_root_endpoint(client: httpx.AsyncClient):
    """Verify GET / returns API metadata and documentation URLs."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "FactLens API"
    assert "documentation" in data
    assert "endpoints" in data
    assert data["endpoints"]["health"] == "/api/health"


@pytest.mark.asyncio
async def test_health_endpoint(client: httpx.AsyncClient):
    """Verify GET /api/health returns system and provider health status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database_connected" in data
    assert "llm_provider" in data
    assert "embedding_provider" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_render_health_check(client: httpx.AsyncClient):
    """Verify GET /health lightweight health check for Render."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "FactLens API"


@pytest.mark.asyncio
async def test_datasets_list(client: httpx.AsyncClient):
    """Verify GET /api/datasets returns a list of datasets."""
    response = await client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "document_count" in first
        assert "fact_count" in first


@pytest.mark.asyncio
async def test_dataset_create_and_get(client: httpx.AsyncClient):
    """Verify POST /api/datasets creates/returns dataset and GET /api/datasets/{id} fetches it."""
    create_resp = await client.post(
        "/api/datasets",
        json={"name": "Test Suite Dataset", "description": "Automated test dataset"},
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "Test Suite Dataset"
    dataset_id = created["id"]

    get_resp = await client.get(f"/api/datasets/{dataset_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == dataset_id
    assert fetched["name"] == "Test Suite Dataset"


@pytest.mark.asyncio
async def test_documents_list(client: httpx.AsyncClient):
    """Verify GET /api/documents returns a list of documents."""
    response = await client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    if docs:
        doc = docs[0]
        assert "id" in doc
        assert "filename" in doc
        assert "page_count" in doc


@pytest.mark.asyncio
async def test_document_detail_not_found(client: httpx.AsyncClient):
    """Verify GET /api/documents/{invalid_id} returns 404."""
    response = await client.get("/api/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reset_processing_not_found(client: httpx.AsyncClient):
    """Verify POST /api/documents/{invalid_id}/reset-processing returns 404 when document doesn't exist."""
    response = await client.post("/api/documents/00000000-0000-0000-0000-000000000000/reset-processing")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reset_processing_success(client: httpx.AsyncClient):
    """Verify POST /api/documents/{id}/reset-processing resets stuck runs successfully."""
    from unittest.mock import patch
    with patch("backend.app.api.documents.get_document_detail", return_value={"id": "11111111-1111-1111-1111-111111111111"}):
        with patch("backend.app.api.documents.reset_document_processing_status", return_value=True):
            response = await client.post("/api/documents/11111111-1111-1111-1111-111111111111/reset-processing")
            assert response.status_code == 200
            data = response.json()
            assert data["reset"] is True
            assert "reset" in data["message"].lower()


@pytest.mark.asyncio
async def test_upload_document_rejects_non_pdf(client: httpx.AsyncClient):
    """Verify POST /api/documents/upload rejects non-PDF files with 400."""
    files = {"file": ("report.txt", b"plain text content", "text/plain")}
    response = await client.post("/api/documents/upload", files=files)
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_facts_list(client: httpx.AsyncClient):
    """Verify GET /api/facts returns paginated facts with evidence citations."""
    response = await client.get("/api/facts?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "facts" in data
    assert isinstance(data["facts"], list)

    if data["facts"]:
        fact = data["facts"][0]
        assert "id" in fact
        assert "entity" in fact
        assert "predicate" in fact
        assert "raw_value" in fact
        assert "evidence" in fact
        assert isinstance(fact["evidence"], list)


@pytest.mark.asyncio
async def test_fact_detail_not_found(client: httpx.AsyncClient):
    """Verify GET /api/facts/{invalid_id} returns 404."""
    response = await client.get("/api/facts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_relationships_list(client: httpx.AsyncClient):
    """Verify GET /api/relationships returns list of cross-document relationships."""
    response = await client.get("/api/relationships")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "relationships" in data
    assert isinstance(data["relationships"], list)

    if data["relationships"]:
        rel = data["relationships"][0]
        assert "id" in rel
        assert "relationship_type" in rel
        assert "confidence" in rel
        assert "rationale" in rel
        assert "fact_a" in rel
        assert "fact_b" in rel


@pytest.mark.asyncio
async def test_four_cases_endpoint(client: httpx.AsyncClient):
    """Verify GET /api/cases/four-cases returns the 4 assignment required cases."""
    response = await client.get("/api/cases/four-cases")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert len(data["cases"]) == 4

    case_types = [c["case_type"] for c in data["cases"]]
    assert "CORROBORATES" in case_types
    assert "CONTRADICTS" in case_types
    assert "CONTEXTUAL_DIFFERENCE" in case_types
    assert "UNCERTAIN" in case_types

    # Verify each case has fact data and reasoning rationale
    for case in data["cases"]:
        assert case["case_number"] in [1, 2, 3, 4]
        assert "fact_a" in case
        assert "system_reasoning" in case
        assert len(case["system_reasoning"]) > 0
