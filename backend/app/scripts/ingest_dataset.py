"""
CLI script to ingest PDF files from a local directory into FactLens.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

from backend.app.services.ingestion_service import IngestionService


async def ingest_directory(dataset_name: str, directory_path: str) -> None:
    path = Path(directory_path)
    if not path.exists() or not path.is_dir():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return

    pdf_files = sorted(list(path.glob("*.pdf")))
    if not pdf_files:
        print(f"No PDF files found in '{directory_path}'.")
        return

    service = IngestionService()
    dataset_id = service.get_or_create_dataset(
        name=dataset_name,
        description=f"Curated dataset for {dataset_name}",
    )
    print(f"Target dataset: '{dataset_name}' (ID: {dataset_id})")
    print(f"Found {len(pdf_files)} PDF file(s) to process:\n")

    for pdf_file in pdf_files:
        print(f"--> Processing: {pdf_file.name} ({pdf_file.stat().st_size / 1024:.1f} KB)")
        with open(pdf_file, "rb") as f:
            file_bytes = f.read()

        result = await service.ingest_pdf(
            file_bytes=file_bytes,
            filename=pdf_file.name,
            dataset_id=dataset_id,
        )

        if result["status"] == "ALREADY_EXISTS":
            print(f"    [Skipped] Already exists (document ID: {result['document_id']})")
        else:
            print(f"    [Success] Ingested {result['page_count']} page(s).")
            print(f"    Document ID:  {result['document_id']}")
            print(f"    Storage Path: {result['storage_path']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Ingest PDFs into FactLens dataset.")
    parser.add_argument("--dataset", required=True, help="Name of dataset (e.g. delhivery)")
    parser.add_argument("--path", required=True, help="Local directory containing PDF files")
    args = parser.parse_args()

    asyncio.run(ingest_directory(dataset_name=args.dataset, directory_path=args.path))


if __name__ == "__main__":
    main()
