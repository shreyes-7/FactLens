"""
CLI Script to execute Relationship Reasoning across candidate facts in Supabase.
Usage:
    uv run python backend/app/scripts/reason_relationships.py
"""

import asyncio
import logging
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.getcwd())

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.config import get_settings
from backend.app.database import get_db_connection, get_fact_relationships
from backend.app.services.reasoning_service import ReasoningService
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("factlens.cli.reason_relationships")


async def main() -> None:
    settings = get_settings()
    service = ReasoningService(settings=settings)

    # 1. Fetch available datasets
    conn = get_db_connection(settings)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM public.datasets ORDER BY created_at ASC;")
            datasets = cur.fetchall()
    finally:
        conn.close()

    if not datasets:
        logger.warning("No datasets found in database.")
        return

    for ds in datasets:
        ds_id = str(ds["id"])
        ds_name = ds["name"]
        print("=" * 80)
        print(f"Executing Relationship Reasoning for Dataset: {ds_name} ({ds_id})")
        print("=" * 80)

        relationships = await service.reason_candidate_pairs_in_dataset(
            dataset_id=ds_id,
            min_similarity=0.45,
            require_cross_document=False,
        )

        print(f"\nReasoned and saved {len(relationships)} relationships into Supabase PostgreSQL:\n")
        for idx, rel in enumerate(relationships, 1):
            print(f"[{idx}] {rel.relationship_type.value} (Confidence: {rel.confidence:.2f} | Method: {rel.reasoning_method})")
            print(f"    Fact A ID: {rel.fact_a_id}")
            print(f"    Fact B ID: {rel.fact_b_id}")
            print(f"    Reason: {rel.reason}")
            if rel.contextual_factors:
                print(f"    Contextual Factors: {rel.contextual_factors}")
            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
