"""
FactLens Processing Service.
Coordinates chunking, embedding generation, LLM fact extraction,
strict evidence grounding, and persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from psycopg2.extras import RealDictCursor

from backend.app.config import Settings, get_settings
from backend.app.database import (
    get_db_connection,
    get_document_pages,
    insert_chunks_batch,
    insert_facts_and_evidence,
    update_processing_run_counts,
)
from backend.app.extraction.fact_extractor import FactExtractor
from backend.app.ingestion.chunker import chunk_page
from backend.app.normalization.normalizer import FactNormalizer
from backend.app.providers.embeddings import get_embedding_provider

from backend.app.providers.embeddings.base import EmbeddingProvider
from backend.app.providers.llm import get_llm_provider
from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger("factlens.processing")


class ProcessingService:
    """Orchestrates chunking, vector embedding, fact extraction, and evidence grounding."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_provider = llm_provider or get_llm_provider(self.settings)
        self.embedding_provider = embedding_provider or get_embedding_provider(self.settings)
        self.fact_extractor = FactExtractor(self.llm_provider)

    async def process_document(
        self,
        document_id: str,
        max_pages: int | None = None,
        page_offset: int = 0,
        page_numbers: list[int] | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> dict[str, Any]:
        """
        Process pages for an ingested document:
          1. Chunk pages with boundary preservation.
          2. Generate 1024-d embeddings via Jina and persist to 'chunks'.
          3. Extract atomic facts with exact quotes via Groq.
          4. Ground evidence against source text with character offsets.
          5. Persist valid facts and evidence links.
          6. Audit metrics in 'processing_runs'.
        """
        doc_uuid = UUID(document_id)
        doc_info = self._get_document_info(str(doc_uuid))
        if not doc_info:
            raise ValueError(f"Document with ID {document_id} not found.")

        dataset_id = str(doc_info["dataset_id"])
        filename = str(doc_info["filename"])

        # Fetch document pages
        all_pages = get_document_pages(str(doc_uuid), self.settings)
        if not all_pages:
            raise ValueError(f"No document pages found for document {document_id}.")

        if page_numbers:
            target_set = set(page_numbers)
            pages_to_process = [p for p in all_pages if p.get("pdf_page_number") in target_set]
        else:
            pages_to_process = all_pages[page_offset:]
            if max_pages is not None:
                pages_to_process = pages_to_process[:max_pages]

        # Initialize or retrieve processing run
        run_id = self._create_processing_run(str(doc_uuid))

        total_chunks = 0
        total_facts = 0
        total_rejected = 0

        logger.info(
            f"Starting processing for '{filename}' ({len(pages_to_process)} pages, run_id={run_id})..."
        )

        try:
            for page in pages_to_process:
                p_id = str(page["id"])
                p_text = page.get("text", "")
                p_num = page.get("pdf_page_number", 1)
                printed_num = page.get("printed_page_number")

                if not p_text.strip():
                    continue

                # 1. Chunk page
                chunks = chunk_page(
                    document_id=doc_uuid,
                    page_id=UUID(p_id),
                    page_text=p_text,
                    pdf_page_number=p_num,
                    printed_page_number=printed_num,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

                if not chunks:
                    continue

                # 2. Generate embeddings
                chunk_texts = [c.text for c in chunks]
                embeddings = await self.embedding_provider.embed_documents(chunk_texts)
                for c, emb in zip(chunks, embeddings):
                    c.embedding = emb

                # 3. Persist chunks and synchronize generated IDs with persisted DB IDs
                chunks_dict = [c.model_dump() for c in chunks]
                persisted_ids = insert_chunks_batch(chunks_dict, self.settings)
                for c, pid in zip(chunks, persisted_ids):
                    c.id = UUID(pid)
                total_chunks += len(chunks)


                # 4. Extract facts from each chunk
                page_facts_with_evidence: list[tuple[dict[str, Any], dict[str, Any]]] = []
                page_rejected = 0

                for c in chunks:
                    facts_with_evidence, rejected = await self.fact_extractor.extract_from_chunk(
                        chunk_text=c.text,
                        document_id=doc_uuid,
                        dataset_id=UUID(dataset_id),
                        page_id=UUID(p_id),
                        chunk_id=c.id,
                        filename=filename,
                        pdf_page_number=p_num,
                        printed_page_number=printed_num,
                        page_text=p_text,
                    )
                    page_rejected += rejected

                    for f_obj, e_obj in facts_with_evidence:
                        FactNormalizer.normalize_fact(f_obj)
                        page_facts_with_evidence.append(
                            (f_obj.model_dump(), e_obj.model_dump())
                        )


                # 5. Persist facts & evidence
                if page_facts_with_evidence:
                    inserted_facts, _ = insert_facts_and_evidence(
                        page_facts_with_evidence, self.settings
                    )
                    total_facts += inserted_facts


                total_rejected += page_rejected

                # Update run counters
                update_processing_run_counts(
                    run_id=run_id,
                    chunks_created=len(chunks),
                    facts_extracted=len(page_facts_with_evidence),
                    facts_rejected=page_rejected,
                    settings=self.settings,
                )

            # Mark run as completed
            self._finalize_processing_run(run_id, status="COMPLETED")
            logger.info(
                f"Completed processing for '{filename}': {total_chunks} chunks, {total_facts} facts, {total_rejected} rejected."
            )

        except Exception as e:
            logger.error(f"Processing failed for document {document_id}: {e}", exc_info=True)
            self._finalize_processing_run(run_id, status="FAILED", error_message=str(e))
            raise e

        return {
            "run_id": run_id,
            "document_id": str(doc_uuid),
            "filename": filename,
            "pages_processed": len(pages_to_process),
            "chunks_created": total_chunks,
            "facts_extracted": total_facts,
            "facts_rejected": total_rejected,
        }

    def _get_document_info(self, document_id: str) -> dict[str, Any] | None:
        conn = get_db_connection(self.settings)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, dataset_id, filename FROM public.documents WHERE id = %s;",
                    (document_id,),
                )
                return cur.fetchone()
        finally:
            conn.close()

    def _create_processing_run(self, document_id: str) -> str:
        run_id = str(uuid4())
        conn = get_db_connection(self.settings)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.processing_runs (
                        id, document_id, status, started_at, model, prompt_version
                    ) VALUES (
                        %s, %s, 'PROCESSING', %s, %s, 'v1.0'
                    );
                    """,
                    (
                        run_id,
                        document_id,
                        datetime.now(timezone.utc),
                        self.settings.groq_model,
                    ),
                )
            return run_id
        finally:
            conn.close()

    def _finalize_processing_run(
        self,
        run_id: str,
        status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> None:
        conn = get_db_connection(self.settings)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.processing_runs
                    SET status = %s,
                        completed_at = %s,
                        error_message = %s
                    WHERE id = %s;
                    """,
                    (status, datetime.now(timezone.utc), error_message, run_id),
                )
        finally:
            conn.close()
