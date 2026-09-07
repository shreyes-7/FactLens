"""
Page-aware chunking engine for FactLens.
Splits document page text into searchable passages while strictly preserving
page boundaries, character offsets, and page metadata.
"""

from typing import Any
from uuid import UUID, uuid4

from backend.app.schemas.chunk import ChunkCreate


def split_text_into_chunks(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[tuple[str, int, int]]:
    """
    Split text into overlapping chunks, tracking (chunk_text, start_offset, end_offset).
    Prefers splitting on paragraph/sentence boundaries where possible.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [(text, 0, len(text))]

    chunks: list[tuple[str, int, int]] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # If not at the end of the text, look for a sensible break point (newline or period)
        if end < text_len:
            # Look for double newline (paragraph break)
            para_break = text.rfind("\n\n", start + chunk_overlap, end)
            if para_break != -1:
                end = para_break + 2
            else:
                # Look for single newline
                line_break = text.rfind("\n", start + chunk_overlap, end)
                if line_break != -1:
                    end = line_break + 1
                else:
                    # Look for sentence end
                    sentence_break = text.rfind(". ", start + chunk_overlap, end)
                    if sentence_break != -1:
                        end = sentence_break + 2
                    else:
                        # Look for space
                        space_break = text.rfind(" ", start + chunk_overlap, end)
                        if space_break != -1:
                            end = space_break + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            # Calculate actual offsets of the trimmed chunk
            actual_start = text.find(chunk_text, start)
            actual_end = actual_start + len(chunk_text)
            chunks.append((chunk_text, actual_start, actual_end))

        if end >= text_len:
            break

        # Move forward, stepping back by overlap
        step = end - chunk_overlap
        if step <= start:
            # Prevent infinite loop if overlap is too large
            step = start + max(1, chunk_size // 2)
        start = step

    return chunks


def chunk_page(
    document_id: UUID | str,
    page_id: UUID | str,
    page_text: str,
    pdf_page_number: int,
    printed_page_number: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[ChunkCreate]:
    """
    Chunk a single document page, generating ChunkCreate objects with offsets and metadata.
    Page boundaries are strictly preserved.
    """
    raw_chunks = split_text_into_chunks(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    doc_uuid = UUID(str(document_id))
    page_uuid = UUID(str(page_id))

    chunk_objects: list[ChunkCreate] = []
    for idx, (chunk_text, start_offset, end_offset) in enumerate(raw_chunks):
        chunk_obj = ChunkCreate(
            id=uuid4(),
            document_id=doc_uuid,
            page_id=page_uuid,
            chunk_index=idx,
            text=chunk_text,
            start_offset=start_offset,
            end_offset=end_offset,
            metadata={
                "pdf_page_number": pdf_page_number,
                "printed_page_number": printed_page_number,
                "char_length": len(chunk_text),
            },
        )
        chunk_objects.append(chunk_obj)

    return chunk_objects


def chunk_document_pages(
    document_id: UUID | str,
    pages: list[dict[str, Any]],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[ChunkCreate]:
    """
    Chunk multiple pages for a document in order.
    Each page's chunks are 0-indexed per page to satisfy unique (page_id, chunk_index).
    """
    all_chunks: list[ChunkCreate] = []
    for page in pages:
        p_id = page["id"]
        p_text = page.get("text", "")
        p_num = page.get("pdf_page_number", 1)
        printed_num = page.get("printed_page_number")
        
        page_chunks = chunk_page(
            document_id=document_id,
            page_id=p_id,
            page_text=p_text,
            pdf_page_number=p_num,
            printed_page_number=printed_num,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(page_chunks)

    return all_chunks
