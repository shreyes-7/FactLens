"""
CLI Script to execute Chunking, Vector Embedding, and Fact Extraction on Ingested Documents.
Usage:
    uv run python backend/app/scripts/process_document.py --document-id <UUID> [--max-pages 5]
    uv run python backend/app/scripts/process_document.py --dataset-name delhivery [--max-pages 3]
"""

import argparse
import asyncio
import logging
import os
import sys
from uuid import UUID

# Ensure project root is in sys.path
sys.path.insert(0, os.getcwd())

from psycopg2.extras import RealDictCursor

from backend.app.config import get_settings

from backend.app.database import get_db_connection
from backend.app.services.processing_service import ProcessingService

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("factlens.cli.process")


def get_documents_for_dataset(dataset_name: str) -> list[dict]:
    settings = get_settings()
    conn = get_db_connection(settings)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT d.id, d.filename, d.page_count
                FROM public.documents d
                JOIN public.datasets ds ON d.dataset_id = ds.id
                WHERE ds.name = %s
                ORDER BY d.created_at ASC;
            """
            cur.execute(query, (dataset_name,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Process ingested documents for chunking and fact extraction.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--document-id", type=str, help="Specific document UUID to process")
    group.add_argument("--dataset-name", type=str, help="Dataset name to process all documents for")
    
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages to process per document")
    parser.add_argument("--page-offset", type=int, default=0, help="Page offset to start processing from")
    parser.add_argument("--pages", type=str, default=None, help="Comma-separated list of PDF page numbers to process (e.g. 4,6,37)")
    parser.add_argument("--chunk-size", type=int, default=800, help="Target chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="Chunk overlap in characters")

    args = parser.parse_args()
    service = ProcessingService()

    page_numbers = None
    if args.pages:
        page_numbers = [int(p.strip()) for p in args.pages.split(",") if p.strip().isdigit()]

    docs_to_process = []
    if args.document_id:
        docs_to_process.append({"id": args.document_id, "filename": "Specified Document"})
    elif args.dataset_name:
        docs_to_process = get_documents_for_dataset(args.dataset_name)
        if not docs_to_process:
            logger.error(f"No documents found for dataset '{args.dataset_name}'.")
            sys.exit(1)

    print(f"\n=======================================================")
    print(f"FactLens Processing Pipeline (Phase 04)")
    print(f"Documents to process: {len(docs_to_process)}")
    print(f"Target pages: {page_numbers if page_numbers else ('Max ' + str(args.max_pages) if args.max_pages is not None else 'ALL')}")
    print(f"LLM Provider: {service.settings.llm_provider} ({service.settings.groq_model})")
    print(f"Embedding Provider: {service.settings.embedding_provider} ({service.settings.embedding_model})")
    print(f"=======================================================\n")

    for doc in docs_to_process:
        doc_id = str(doc["id"])
        fname = doc.get("filename", doc_id)
        print(f"--> Processing document: {fname} (ID: {doc_id})")

        try:
            result = asyncio.run(
                service.process_document(
                    document_id=doc_id,
                    max_pages=args.max_pages,
                    page_offset=args.page_offset,
                    page_numbers=page_numbers,
                    chunk_size=args.chunk_size,
                    chunk_overlap=args.chunk_overlap,
                )
            )

            print(f"  [OK] Run ID: {result['run_id']}")

            print(f"       Pages Processed:  {result['pages_processed']}")
            print(f"       Chunks Created:   {result['chunks_created']}")
            print(f"       Facts Extracted:  {result['facts_extracted']}")
            print(f"       Facts Rejected:   {result['facts_rejected']}\n")

        except Exception as e:
            print(f"  [ERROR] Processing failed: {e}\n")


if __name__ == "__main__":
    main()
