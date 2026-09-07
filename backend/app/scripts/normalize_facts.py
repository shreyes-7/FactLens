"""
CLI Script to execute Fact Normalization on all facts stored in Supabase.
Usage:
    uv run python backend/app/scripts/normalize_facts.py [--dataset-name delhivery]
"""

import argparse
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.getcwd())

from psycopg2.extras import RealDictCursor

from backend.app.config import get_settings
from backend.app.database import get_all_facts, get_db_connection
from backend.app.services.normalization_service import NormalizationService

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def get_dataset_id_by_name(dataset_name: str) -> str | None:
    settings = get_settings()
    conn = get_db_connection(settings)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM public.datasets WHERE name = %s;", (dataset_name,))
            row = cur.fetchone()
            return str(row["id"]) if row else None
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Normalize facts stored in Supabase PostgreSQL.")
    parser.add_argument("--dataset-name", type=str, default=None, help="Filter by dataset name")
    args = parser.parse_args()

    dataset_id = None
    if args.dataset_name:
        dataset_id = get_dataset_id_by_name(args.dataset_name)
        if not dataset_id:
            print(f"Error: Dataset '{args.dataset_name}' not found.")
            sys.exit(1)

    print("\n=======================================================")
    print("FactLens Fact Normalization Engine (Phase 05)")
    print(f"Target Dataset: {args.dataset_name or 'ALL DATASETS'}")
    print("=======================================================\n")

    service = NormalizationService()
    result = service.normalize_stored_facts(dataset_id=dataset_id)

    print(f"[OK] Normalization complete!")
    print(f"     Total facts scanned:  {result['total_facts']}")
    print(f"     Facts updated in DB:  {result['updated_count']}\n")

    # Display normalized samples
    facts = get_all_facts(dataset_id=dataset_id, settings=service.settings)
    print("Sample Normalized Facts:")
    print("-" * 80)
    for f in facts[:10]:
        print(f"Subject:    {f['subject']} | Predicate: {f['predicate']}")
        print(f"Raw Value:  {f['value_numeric']} ({f['raw_value_text']}) {f['unit']} -> Period: {f['period_text']}")
        print(f"Normalized: {f['normalized_value_numeric']} {f['normalized_unit']} -> Bounds: {f['period_start']} .. {f['period_end']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
