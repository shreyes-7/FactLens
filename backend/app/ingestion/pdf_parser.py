"""
PDF Parser module for FactLens.
Extracts page-by-page text and structural metadata using PyMuPDF (fitz)
without flattening pages into a single string.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
import pymupdf as fitz


@dataclass
class ParsedPage:
    """Represents a single parsed PDF page."""

    pdf_page_number: int  # 1-indexed (must be > 0)
    printed_page_number: str | None
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Represents an entire parsed PDF document."""

    filename: str
    file_hash: str  # SHA-256
    page_count: int
    title: str | None
    metadata: dict[str, Any]
    pages: list[ParsedPage]


def compute_file_hash(file_bytes: bytes) -> str:
    """Compute standard SHA-256 hash for document content."""
    return hashlib.sha256(file_bytes).hexdigest()


def detect_printed_page_number(page_text: str, pdf_page_num: int) -> str | None:
    """
    Attempt to detect a printed page number in the header or footer of the page text.
    Falls back to string of pdf_page_number if a printed number cannot be reliably determined.
    """
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return str(pdf_page_num)

    # Check bottom line (footer) and top line (header)
    for candidate_line in (lines[-1], lines[0]):
        # Match "Page 12", "12", "p. 12", "- 12 -"
        match = re.search(r"^(?:page\s*|p\.?\s*|-?\s*)?(\d{1,4})(?:\s*-)?$", candidate_line, re.IGNORECASE)
        if match:
            return match.group(1)

    return str(pdf_page_num)


def parse_pdf(file_bytes: bytes, filename: str = "document.pdf") -> ParsedDocument:
    """
    Parse PDF from in-memory bytes page-by-page.
    Preserves exact page numbers, metadata, and per-page boundaries.
    """
    file_hash = compute_file_hash(file_bytes)

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Failed to open PDF document '{filename}': {exc}") from exc

    page_count = len(doc)
    doc_metadata = doc.metadata or {}
    title = doc_metadata.get("title") or filename

    parsed_pages: list[ParsedPage] = []

    for idx in range(page_count):
        page = doc[idx]
        pdf_page_number = idx + 1  # 1-indexed

        # Extract text preserving layout
        page_text = page.get_text("text") or ""
        printed_page_number = detect_printed_page_number(page_text, pdf_page_number)

        rect = page.rect
        page_meta = {
            "width": float(rect.width),
            "height": float(rect.height),
            "char_count": len(page_text),
            "word_count": len(page_text.split()),
        }

        parsed_pages.append(
            ParsedPage(
                pdf_page_number=pdf_page_number,
                printed_page_number=printed_page_number,
                text=page_text,
                metadata=page_meta,
            )
        )

    doc.close()

    return ParsedDocument(
        filename=filename,
        file_hash=file_hash,
        page_count=page_count,
        title=title,
        metadata={
            "author": doc_metadata.get("author"),
            "subject": doc_metadata.get("subject"),
            "creator": doc_metadata.get("creator"),
            "producer": doc_metadata.get("producer"),
            "creation_date": doc_metadata.get("creationDate"),
            "mod_date": doc_metadata.get("modDate"),
        },
        pages=parsed_pages,
    )
