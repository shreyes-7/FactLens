"""
FactLens Ingestion Service.
Orchestrates PDF file storage, document record persistence, page extraction,
and processing run tracking.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from psycopg2.extras import RealDictCursor

from backend.app.config import Settings, get_settings
from backend.app.database import get_db_connection
from backend.app.storage.supabase_storage import SupabaseStorageClient
from backend.app.ingestion.pdf_parser import parse_pdf, compute_file_hash

logger = logging.getLogger("factlens.ingestion")


class IngestionService:
    """Service to handle dataset registration, PDF storage, and page parsing."""

    def __init__(
        self,
        storage_client: SupabaseStorageClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = storage_client or SupabaseStorageClient(self.settings)

    def get_or_create_dataset(self, name: str, description: str | None = None) -> str:
        """Find an existing dataset by name or insert a new one. Returns dataset UUID."""
        conn = get_db_connection(self.settings)
        conn.autocommit = True
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM public.datasets WHERE name = %s;", (name,))
                row = cur.fetchone()
                if row:
                    return str(row["id"])

                dataset_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO public.datasets (id, name, description) VALUES (%s, %s, %s) RETURNING id;",
                    (dataset_id, name, description or f"Dataset: {name}"),
                )
                created = cur.fetchone()
                return str(created["id"])
        finally:
            conn.close()

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        dataset_id: str,
    ) -> dict[str, Any]:
        """
        Ingest a PDF:
        1. Verify deduplication by (dataset_id, file_hash).
        2. Upload binary to Supabase Storage.
        3. Parse PDF page-by-page.
        4. Insert document and page records.
        5. Log processing run.
        """
        file_hash = compute_file_hash(file_bytes)
        conn = get_db_connection(self.settings)
        conn.autocommit = True

        try:
            # 1. Deduplication check
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, filename, page_count, storage_path FROM public.documents WHERE dataset_id = %s AND file_hash = %s;",
                    (dataset_id, file_hash),
                )
                existing = cur.fetchone()
                if existing:
                    logger.info("Document '%s' already exists in dataset %s.", filename, dataset_id)
                    return {
                        "status": "ALREADY_EXISTS",
                        "document_id": str(existing["id"]),
                        "dataset_id": dataset_id,
                        "filename": existing["filename"],
                        "page_count": existing["page_count"],
                        "storage_path": existing["storage_path"],
                    }

            # 2. Parse PDF pages
            parsed_doc = parse_pdf(file_bytes, filename=filename)
            document_id = str(uuid.uuid4())
            run_id = str(uuid.uuid4())
            started_at = datetime.now(timezone.utc)

            # 3. Upload to Supabase Storage
            storage_path = self.storage.get_canonical_path(dataset_id, document_id, filename)
            await self.storage.ensure_bucket_exists()
            full_storage_path = await self.storage.upload_file(file_bytes, storage_path)

            # 4. Insert Document Record
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.documents
                    (id, dataset_id, filename, title, file_hash, storage_path, page_count, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        document_id,
                        dataset_id,
                        filename,
                        parsed_doc.title,
                        file_hash,
                        full_storage_path,
                        parsed_doc.page_count,
                        json.dumps(parsed_doc.metadata),
                    ),
                )

                # 5. Record processing run (PROCESSING)
                cur.execute(
                    """
                    INSERT INTO public.processing_runs
                    (id, document_id, status, started_at, model, prompt_version, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        run_id,
                        document_id,
                        "PROCESSING",
                        started_at,
                        "PyMuPDF",
                        "pdf_v1",
                        json.dumps({"filename": filename, "file_hash": file_hash}),
                    ),
                )

                # 6. Insert Page Records
                for page in parsed_doc.pages:
                    page_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO public.document_pages
                        (id, document_id, pdf_page_number, printed_page_number, text, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb);
                        """,
                        (
                            page_id,
                            document_id,
                            page.pdf_page_number,
                            page.printed_page_number,
                            page.text,
                            json.dumps(page.metadata),
                        ),
                    )

                # 7. Complete processing run
                completed_at = datetime.now(timezone.utc)
                cur.execute(
                    """
                    UPDATE public.processing_runs
                    SET status = %s, completed_at = %s, pages_processed = %s
                    WHERE id = %s;
                    """,
                    ("COMPLETED", completed_at, parsed_doc.page_count, run_id),
                )

            logger.info(
                "Ingested document '%s' (id: %s, %d pages)",
                filename,
                document_id,
                parsed_doc.page_count,
            )

            return {
                "status": "COMPLETED",
                "document_id": document_id,
                "dataset_id": dataset_id,
                "filename": filename,
                "title": parsed_doc.title,
                "page_count": parsed_doc.page_count,
                "storage_path": full_storage_path,
                "run_id": run_id,
            }

        finally:
            conn.close()
