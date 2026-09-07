"""
Unit tests for the PDF parser module.
"""

import fitz  # PyMuPDF
from backend.app.ingestion.pdf_parser import parse_pdf, compute_file_hash, detect_printed_page_number


def create_sample_pdf_bytes(page_texts: list[str]) -> bytes:
    """Helper to generate an in-memory PDF using PyMuPDF."""
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((50, 50), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_parsing_page_preservation():
    """Verify that pages are extracted with exact 1-indexed numbers and preserved text."""
    pages = [
        "First page content of financial report.\nRevenue reached 100M.",
        "Second page content.\nEBITDA was positive.",
    ]
    pdf_bytes = create_sample_pdf_bytes(pages)
    parsed = parse_pdf(pdf_bytes, filename="sample_report.pdf")

    assert parsed.filename == "sample_report.pdf"
    assert parsed.page_count == 2
    assert parsed.file_hash == compute_file_hash(pdf_bytes)
    assert len(parsed.pages) == 2

    # Verify Page 1
    assert parsed.pages[0].pdf_page_number == 1
    assert "First page content" in parsed.pages[0].text
    assert parsed.pages[0].metadata["width"] == 595.0
    assert parsed.pages[0].metadata["height"] == 842.0

    # Verify Page 2
    assert parsed.pages[1].pdf_page_number == 2
    assert "Second page content" in parsed.pages[1].text


def test_detect_printed_page_number():
    """Verify detection of printed page numbers in header or footer."""
    text_with_footer = "Paragraph 1\nParagraph 2\nPage 42"
    assert detect_printed_page_number(text_with_footer, 42) == "42"

    text_plain = "Paragraph 1\nParagraph 2"
    assert detect_printed_page_number(text_plain, 5) == "5"
