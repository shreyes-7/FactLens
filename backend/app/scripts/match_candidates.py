"""
CLI script to generate embeddings for extracted facts and discover cross-document candidate pairs.
Usage:
    uv run python backend/app/scripts/match_candidates.py
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
from backend.app.database import get_all_facts, get_db_connection
from backend.app.services.matching_service import MatchingService
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("factlens.cli.match_candidates")


async def main() -> None:
    settings = get_settings()
    service = MatchingService(settings=settings)

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
        print(f"Dataset: {ds_name} (ID: {ds_id})")
        print("=" * 80)

        # 2. Embed unembedded facts
        embedded_count = await service.embed_unembedded_facts(dataset_id=ds_id)
        print(f"Generated embeddings for {embedded_count} newly embedded facts.")

        # 3. Discover candidates across documents
        print("\nSearching for candidate fact pairs (min_similarity=0.45)...")
        response = await service.discover_candidates_in_dataset(
            dataset_id=ds_id,
            min_similarity=0.45,
            require_cross_document=True,
        )

        print(f"\nDiscovered {response.total_candidates} cross-document candidate pairs:")
        for idx, pair in enumerate(response.candidates, 1):
            print(f"\n--- Candidate Pair #{idx} [Similarity Score: {pair.similarity_score:.4f}] ---")
            print(f"Fact A: {pair.fact_a_id}")
            print(f"Fact B: {pair.fact_b_id}")
            print(f"Subject Match: {pair.subject_match} | Predicate Match: {pair.predicate_match} | Temporal Overlap: {pair.temporal_overlap}")
            print(f"Match Reasons: {', '.join(pair.match_reasons)}")
            if pair.metadata:
                print(f"Claim A: {pair.metadata.get('fact_a_claim')}")
                print(f"Claim B: {pair.metadata.get('fact_b_claim')}")


if __name__ == "__main__":
    asyncio.run(main())
