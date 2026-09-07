"""
Fact Extraction and Evidence Grounding Engine for FactLens.
Orchestrates LLM calls, validates structured Pydantic schemas,
and strictly verifies that evidence quotes are grounded in source text.
"""

import json
import logging
import re
from typing import Any
from uuid import UUID, uuid4

from backend.app.extraction.prompts import (
    BATCH_FACT_EXTRACTION_SYSTEM_PROMPT,
    BATCH_FACT_EXTRACTION_USER_PROMPT,
    FACT_EXTRACTION_SYSTEM_PROMPT,
    FACT_EXTRACTION_USER_PROMPT,
)
from backend.app.providers.llm.base import LLMProvider
from backend.app.schemas.chunk import ChunkCreate
from backend.app.schemas.evidence import EvidenceCreate
from backend.app.schemas.fact import FactCreate, FactType
from backend.app.schemas.llm_extraction import ExtractedFactItem, FactExtractionBatch

logger = logging.getLogger(__name__)


def locate_quote_in_text(quote: str, text: str) -> tuple[int | None, int | None, bool]:
    """
    Locate quote in text.
    Returns: (start_offset, end_offset, is_grounded).
    Tries:
      1. Exact substring match.
      2. Whitespace-insensitive regex match (handling arbitrary newlines/spaces).
    """
    if not quote or not text:
        return None, None, False

    # 1. Exact match
    idx = text.find(quote)
    if idx != -1:
        return idx, idx + len(quote), True

    # 2. Whitespace-insensitive regex match
    words = quote.split()
    if not words:
        return None, None, False

    pattern = r"\s+".join(re.escape(w) for w in words)
    match = re.search(pattern, text)
    if match:
        return match.start(), match.end(), True

    return None, None, False


class FactExtractor:
    """
    Extracts atomic facts and verifies evidence quotes against source passages.
    Supports both batched chunk extraction (recommended) and single-chunk extraction.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def extract_from_batch(
        self,
        chunks: list[ChunkCreate],
        document_id: UUID | str,
        dataset_id: UUID | str,
        filename: str = "document.pdf",
        page_texts: dict[str, str] | None = None,
    ) -> tuple[list[tuple[FactCreate, EvidenceCreate]], int]:
        """
        Extract facts from a batch of sequential text chunks.
        Evaluates every chunk independently, preserves source chunk IDs,
        and strictly verifies evidence grounding.
        """
        if not chunks:
            return [], 0

        doc_uuid = UUID(str(document_id))
        ds_uuid = UUID(str(dataset_id))

        # Build mapping for chunk lookup by label, index, and UUID
        chunk_map: dict[str, ChunkCreate] = {}
        chunk_entries: list[str] = []

        for i, c in enumerate(chunks, 1):
            label = f"chunk_{i}"
            chunk_map[label] = c
            chunk_map[f"chunk {i}"] = c
            chunk_map[str(i)] = c
            if c.id:
                chunk_map[str(c.id)] = c
                chunk_map[str(c.id).lower()] = c

            pdf_page = c.metadata.get("pdf_page_number", 1) if c.metadata else 1
            chunk_entries.append(
                f"--- CHUNK [ID: {label}] (Page {pdf_page}) ---\n{c.text}"
            )

        chunks_content = "\n\n".join(chunk_entries)
        user_prompt = BATCH_FACT_EXTRACTION_USER_PROMPT.format(
            filename=filename,
            batch_count=len(chunks),
            chunks_content=chunks_content,
        )

        try:
            raw_response = await self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=BATCH_FACT_EXTRACTION_SYSTEM_PROMPT,
            )
        except Exception as e:
            logger.error(f"LLM generation failed for chunk batch ({len(chunks)} chunks): {e}")
            return [], 0

        batch = self._parse_llm_response(raw_response)
        if not batch or not batch.facts:
            return [], 0

        accepted: list[tuple[FactCreate, EvidenceCreate]] = []
        rejected_count = 0

        for item in batch.facts:
            # 1. Resolve source chunk
            target_chunk: ChunkCreate | None = None
            if item.chunk_id:
                cid_clean = str(item.chunk_id).strip().lower()
                target_chunk = chunk_map.get(cid_clean) or chunk_map.get(str(item.chunk_id).strip())

            # Fallback: find which chunk in the batch contains the quote
            if not target_chunk:
                for c in chunks:
                    if item.quote and item.quote in c.text:
                        target_chunk = c
                        break

            # Secondary fallback: find by whitespace-insensitive match in batch chunks
            if not target_chunk:
                for c in chunks:
                    _, _, grounded_in_c = locate_quote_in_text(item.quote, c.text)
                    if grounded_in_c:
                        target_chunk = c
                        break

            if not target_chunk:
                # If still not found, check if it's in page_texts
                found_in_page = False
                if page_texts:
                    for p_id_str, p_txt in page_texts.items():
                        _, _, grounded_p = locate_quote_in_text(item.quote, p_txt)
                        if grounded_p:
                            found_in_page = True
                            for c in chunks:
                                if str(c.page_id) == p_id_str:
                                    target_chunk = c
                                    break
                            break

                if not target_chunk or not found_in_page:
                    logger.warning(
                        f"Rejecting hallucinated fact (quote not found in batch chunks): '{item.quote[:60]}...'"
                    )
                    rejected_count += 1
                    continue

            # 2. Evidence Grounding Verification within resolved chunk or page
            start_offset, end_offset, is_grounded = locate_quote_in_text(item.quote, target_chunk.text)
            if not is_grounded:
                p_text = page_texts.get(str(target_chunk.page_id)) if page_texts else None
                if p_text:
                    start_offset, end_offset, is_grounded = locate_quote_in_text(item.quote, p_text)

            if not is_grounded:
                logger.warning(
                    f"Rejecting ungrounded quote for fact '{item.predicate}': '{item.quote[:60]}...'"
                )
                rejected_count += 1
                continue

            # 3. Construct Fact model
            fact_id = uuid4()
            val_text = item.value_text
            val_num = item.value_numeric
            val_bool = item.value_boolean
            if val_text is None and val_num is None and val_bool is None:
                val_text = item.raw_value_text or item.raw_claim

            pdf_page_num = target_chunk.metadata.get("pdf_page_number", 1) if target_chunk.metadata else 1
            printed_page_num = target_chunk.metadata.get("printed_page_number") if target_chunk.metadata else None

            try:
                fact_obj = FactCreate(
                    id=fact_id,
                    dataset_id=ds_uuid,
                    document_id=doc_uuid,
                    subject=item.subject.strip(),
                    predicate=item.predicate.strip(),
                    raw_claim=item.raw_claim.strip(),
                    value_text=val_text,
                    raw_value_text=item.raw_value_text or val_text or str(val_num or ""),
                    value_numeric=val_num,
                    value_boolean=val_bool,
                    unit=item.unit,
                    normalized_unit=None,
                    fact_type=item.fact_type,
                    period_text=item.period_text,
                    scope=item.scope,
                    geography=item.geography,
                    segment=item.segment,
                    status=item.status,
                    attribution=item.attribution,
                    confidence=min(1.0, max(0.0, float(item.confidence))),
                    qualifiers={},
                    metadata={
                        "pdf_page_number": pdf_page_num,
                        "printed_page_number": printed_page_num,
                        "chunk_id": str(target_chunk.id) if target_chunk.id else None,
                    },
                )
            except Exception as e:
                logger.warning(f"Fact validation failed: {e}. Rejecting fact.")
                rejected_count += 1
                continue

            # 4. Construct Evidence model
            evidence_obj = EvidenceCreate(
                id=uuid4(),
                fact_id=fact_id,
                document_id=doc_uuid,
                page_id=target_chunk.page_id,
                chunk_id=target_chunk.id,
                quote=item.quote.strip(),
                start_offset=start_offset,
                end_offset=end_offset,
                extraction_method="gemini_batch_structured_extraction",
                extraction_confidence=fact_obj.confidence,
                metadata={
                    "pdf_page_number": pdf_page_num,
                    "printed_page_number": printed_page_num,
                },
            )

            accepted.append((fact_obj, evidence_obj))

        return accepted, rejected_count

    async def extract_from_chunk(
        self,
        chunk_text: str,
        document_id: UUID | str,
        dataset_id: UUID | str,
        page_id: UUID | str,
        chunk_id: UUID | str | None,
        filename: str = "document.pdf",
        pdf_page_number: int = 1,
        printed_page_number: str | None = None,
        page_text: str | None = None,
    ) -> tuple[list[tuple[FactCreate, EvidenceCreate]], int]:
        """
        Extract facts from a single text chunk.
        Returns:
            (valid_facts_with_evidence, rejected_count)
        """
        if not chunk_text or len(chunk_text.strip()) < 30:
            return [], 0

        doc_uuid = UUID(str(document_id))
        ds_uuid = UUID(str(dataset_id))
        page_uuid = UUID(str(page_id))
        chunk_uuid = UUID(str(chunk_id)) if chunk_id else None

        user_prompt = FACT_EXTRACTION_USER_PROMPT.format(
            filename=filename,
            pdf_page_number=pdf_page_number,
            printed_page_number=printed_page_number or "N/A",
            text=chunk_text,
        )

        try:
            raw_response = await self.llm_provider.generate(
                prompt=user_prompt,
                system_prompt=FACT_EXTRACTION_SYSTEM_PROMPT,
            )
        except Exception as e:
            logger.error(f"LLM generation failed for page {pdf_page_number}: {e}")
            return [], 0

        batch = self._parse_llm_response(raw_response)
        if not batch or not batch.facts:
            return [], 0

        search_context = page_text if page_text else chunk_text
        accepted: list[tuple[FactCreate, EvidenceCreate]] = []
        rejected_count = 0

        for item in batch.facts:
            # 1. Evidence Grounding Verification
            start_offset, end_offset, is_grounded = locate_quote_in_text(item.quote, search_context)
            if not is_grounded:
                logger.warning(
                    f"Rejecting hallucinated fact (quote not found in text): '{item.quote[:60]}...'"
                )
                rejected_count += 1
                continue

            # 2. Construct Fact model
            fact_id = uuid4()
            val_text = item.value_text
            val_num = item.value_numeric
            val_bool = item.value_boolean
            if val_text is None and val_num is None and val_bool is None:
                val_text = item.raw_value_text or item.raw_claim

            try:
                fact_obj = FactCreate(
                    id=fact_id,
                    dataset_id=ds_uuid,
                    document_id=doc_uuid,
                    subject=item.subject.strip(),
                    predicate=item.predicate.strip(),
                    raw_claim=item.raw_claim.strip(),
                    value_text=val_text,
                    raw_value_text=item.raw_value_text or val_text or str(val_num or ""),
                    value_numeric=val_num,
                    value_boolean=val_bool,
                    unit=item.unit,
                    normalized_unit=None,  # Handled in Phase 05
                    fact_type=item.fact_type,
                    period_text=item.period_text,
                    scope=item.scope,
                    geography=item.geography,
                    segment=item.segment,
                    status=item.status,
                    attribution=item.attribution,
                    confidence=min(1.0, max(0.0, float(item.confidence))),
                    qualifiers={},
                    metadata={
                        "pdf_page_number": pdf_page_number,
                        "printed_page_number": printed_page_number,
                    },
                )

            except Exception as e:
                logger.warning(f"Fact validation failed: {e}. Rejecting fact.")
                rejected_count += 1
                continue

            # 3. Construct Evidence model
            evidence_obj = EvidenceCreate(
                id=uuid4(),
                fact_id=fact_id,
                document_id=doc_uuid,
                page_id=page_uuid,
                chunk_id=chunk_uuid,
                quote=item.quote.strip(),
                start_offset=start_offset,
                end_offset=end_offset,
                extraction_method="groq_structured_extraction",
                extraction_confidence=fact_obj.confidence,
                metadata={
                    "pdf_page_number": pdf_page_number,
                    "printed_page_number": printed_page_number,
                },
            )

            accepted.append((fact_obj, evidence_obj))

        return accepted, rejected_count

    def _parse_llm_response(self, raw_text: str) -> FactExtractionBatch | None:
        """Extract and validate JSON from LLM response text."""
        cleaned = raw_text.strip()
        # Strip markdown code blocks if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Find JSON object boundaries if extra text exists
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

        try:
            data = json.loads(cleaned)
            return FactExtractionBatch.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nRaw output: {raw_text[:200]}")
            return None
