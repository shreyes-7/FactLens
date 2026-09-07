"""
FactLens Processing Service.
Coordinates chunking, embedding generation, LLM fact extraction,
strict evidence grounding, and persistence.
"""

from contextlib import nullcontext
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

try:
    import logfire
except ImportError:
    logfire = None

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
from backend.app.schemas.chunk import ChunkCreate

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
        self.fact_extractor = FactExtractor(llm_provider=self.llm_provider)

    async def process_document(
        self,
        document_id: UUID | str,
        max_pages: int | None = None,
        page_offset: int = 0,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        page_numbers: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the end-to-end processing pipeline for a document using controlled chunk batching.
        1. Parse pages.
        2. Chunk text with page boundary preservation.
        3. Generate semantic vector embeddings.
        4. Group chunks into controlled batches (FACT_EXTRACTION_BATCH_SIZE).
        5. Extract facts via LLM with chunk ID preservation and evidence grounding.
        6. Normalize and persist facts & evidence with deduplication.
        """
        doc_uuid = UUID(str(document_id))
        doc_info = self._get_document_info(str(doc_uuid))
        if not doc_info:
            raise ValueError(f"Document with ID {document_id} does not exist.")

        filename = doc_info.get("filename", "document.pdf")
        dataset_id = str(doc_info["dataset_id"])

        # Check for concurrent processing run to avoid duplicate execution
        active_run = self._check_active_run(str(doc_uuid))
        if active_run:
            logger.warning(
                f"Document '{filename}' already has an active processing run ({active_run['id']}). Skipping concurrent execution."
            )
            return {
                "run_id": active_run["id"],
                "document_id": str(doc_uuid),
                "filename": filename,
                "status": "ALREADY_PROCESSING",
                "message": "Document is already being processed.",
            }

        # Fetch document pages
        all_pages = get_document_pages(str(doc_uuid), self.settings)
        if not all_pages:
            raise ValueError(f"No pages found for document {document_id}.")

        # Filter target pages
        if page_numbers is not None and len(page_numbers) > 0:
            target_set = set(page_numbers)
            pages_to_process = [p for p in all_pages if p.get("pdf_page_number") in target_set]
        else:
            pages_to_process = all_pages[page_offset:]
            if max_pages is not None:
                pages_to_process = pages_to_process[:max_pages]

        # Initialize processing run
        run_id = self._create_processing_run(str(doc_uuid))

        total_chunks = 0
        total_facts = 0
        total_rejected = 0

        logger.info(
            f"Starting processing for '{filename}' ({len(pages_to_process)} pages, run_id={run_id})..."
        )

        try:
            # 1. Chunk and embed all target pages in sequential document order
            all_chunks: list[ChunkCreate] = []
            page_texts: dict[str, str] = {}

            for page in pages_to_process:
                p_id = str(page["id"])
                p_text = page.get("text", "")
                p_num = page.get("pdf_page_number", 1)
                printed_num = page.get("printed_page_number")

                if not p_text.strip():
                    continue

                page_texts[p_id] = p_text

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

                # Generate embeddings
                chunk_texts = [c.text for c in chunks]
                embeddings = await self.embedding_provider.embed_documents(chunk_texts)
                for c, emb in zip(chunks, embeddings):
                    c.embedding = emb

                # Persist chunks and synchronize DB UUIDs
                chunks_dict = [c.model_dump() for c in chunks]
                persisted_ids = insert_chunks_batch(chunks_dict, self.settings)
                for c, pid in zip(chunks, persisted_ids):
                    c.id = UUID(pid)

                all_chunks.extend(chunks)

            total_chunks = len(all_chunks)
            update_processing_run_counts(
                run_id=run_id,
                chunks_created=total_chunks,
                settings=self.settings,
            )

            if not all_chunks:
                logger.info(f"No chunks generated for '{filename}'. Completing run.")
                self._finalize_processing_run(run_id, status="COMPLETED")
                return {
                    "run_id": run_id,
                    "document_id": str(doc_uuid),
                    "filename": filename,
                    "pages_processed": len(pages_to_process),
                    "chunks_created": 0,
                    "facts_extracted": 0,
                    "facts_rejected": 0,
                }

            # 2. Partition chunks into controlled batches of size FACT_EXTRACTION_BATCH_SIZE
            batch_size = max(1, self.settings.fact_extraction_batch_size)
            chunk_batches = [
                all_chunks[i : i + batch_size]
                for i in range(0, len(all_chunks), batch_size)
            ]
            total_batches = len(chunk_batches)

            logger.info(
                f"Fact extraction: {total_chunks} chunks partitioned into {total_batches} batches "
                f"(batch_size={batch_size}) for '{filename}'."
            )

            import time

            # 3. Process batches sequentially
            for batch_idx, batch in enumerate(chunk_batches, 1):
                start_time = time.perf_counter()
                span_cm = (
                    logfire.span(
                        "fact_extraction_batch",
                        document_id=str(doc_uuid),
                        filename=filename,
                        batch_number=batch_idx,
                        total_batches=total_batches,
                        batch_size=len(batch),
                        llm_provider=self.llm_provider.provider_name,
                        llm_model=self.llm_provider.model_name,
                    )
                    if logfire
                    else nullcontext()
                )

                with span_cm:
                    try:
                        facts_with_evidence, rejected = await self.fact_extractor.extract_from_batch(
                            chunks=batch,
                            document_id=doc_uuid,
                            dataset_id=UUID(dataset_id),
                            filename=filename,
                            page_texts=page_texts,
                        )

                        batch_facts_with_evidence: list[tuple[dict[str, Any], dict[str, Any]]] = []
                        for f_obj, e_obj in facts_with_evidence:
                            FactNormalizer.normalize_fact(f_obj)
                            batch_facts_with_evidence.append(
                                (f_obj.model_dump(), e_obj.model_dump())
                            )

                        # Persist batch facts & evidence immediately
                        if batch_facts_with_evidence:
                            inserted_count, _ = insert_facts_and_evidence(
                                batch_facts_with_evidence, self.settings
                            )
                            total_facts += inserted_count

                        total_rejected += rejected

                        # Update run counters
                        update_processing_run_counts(
                            run_id=run_id,
                            chunks_created=0,
                            facts_extracted=len(batch_facts_with_evidence),
                            facts_rejected=rejected,
                            settings=self.settings,
                        )

                        duration = time.perf_counter() - start_time
                        logger.info(
                            f"Batch {batch_idx}/{total_batches} complete ({duration:.2f}s, provider={self.llm_provider.provider_name}): "
                            f"{len(batch_facts_with_evidence)} facts extracted, {rejected} rejected."
                        )

                    except Exception as batch_err:
                        logger.error(
                            f"Batch {batch_idx}/{total_batches} failed during fact extraction: {batch_err}",
                            exc_info=True,
                        )
                        # Succeeded batches remain safely persisted!

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

    def _check_active_run(self, document_id: str) -> dict[str, Any] | None:
        """Check if an active processing run is currently in progress for this document."""
        conn = get_db_connection(self.settings)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, status, started_at
                    FROM public.processing_runs
                    WHERE document_id = %s AND status = 'PROCESSING'
                    ORDER BY started_at DESC
                    LIMIT 1;
                    """,
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
                        %s, %s, 'PROCESSING', %s, %s, 'v2.0-batch'
                    );
                    """,
                    (
                        run_id,
                        document_id,
                        datetime.now(timezone.utc),
                        f"{self.llm_provider.provider_name}:{self.llm_provider.model_name}",
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
