"""
Unit tests for page-aware chunking engine.
"""

from uuid import uuid4
import pytest

from backend.app.ingestion.chunker import (
    chunk_document_pages,
    chunk_page,
    split_text_into_chunks,
)


def test_split_short_text():
    text = "Short sentence that easily fits in one chunk."
    chunks = split_text_into_chunks(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) == 1
    chunk_text, start, end = chunks[0]
    assert chunk_text == text
    assert start == 0
    assert end == len(text)


def test_split_empty_text():
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   \n\t  ") == []


def test_split_long_text_with_overlap():
    text = (
        "Paragraph 1 contains financial disclosures. " * 5
        + "\n\n"
        + "Paragraph 2 details operational revenue and shipment metrics. " * 5
    )
    chunks = split_text_into_chunks(text, chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1

    for chunk_text, start, end in chunks:
        assert len(chunk_text) > 0
        assert text[start:end] == chunk_text


def test_chunk_page_preserves_metadata():
    doc_id = uuid4()
    page_id = uuid4()
    page_text = "Delhivery recorded Rs. 127 Cr EBITDA in FY24. This reflects substantial growth."

    chunks = chunk_page(
        document_id=doc_id,
        page_id=page_id,
        page_text=page_text,
        pdf_page_number=5,
        printed_page_number="iv",
        chunk_size=500,
    )

    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_id == doc_id
    assert c.page_id == page_id
    assert c.chunk_index == 0
    assert c.text == page_text
    assert c.start_offset == 0
    assert c.end_offset == len(page_text)
    assert c.metadata["pdf_page_number"] == 5
    assert c.metadata["printed_page_number"] == "iv"


def test_chunk_document_pages_never_merges_across_pages():
    doc_id = uuid4()
    pages = [
        {"id": uuid4(), "text": "Page 1 unique text content.", "pdf_page_number": 1},
        {"id": uuid4(), "text": "Page 2 unique text content.", "pdf_page_number": 2},
    ]

    all_chunks = chunk_document_pages(doc_id, pages, chunk_size=500)
    assert len(all_chunks) == 2
    assert all_chunks[0].page_id == pages[0]["id"]
    assert all_chunks[0].chunk_index == 0
    assert all_chunks[0].metadata["pdf_page_number"] == 1

    assert all_chunks[1].page_id == pages[1]["id"]
    assert all_chunks[1].chunk_index == 0
    assert all_chunks[1].metadata["pdf_page_number"] == 2
