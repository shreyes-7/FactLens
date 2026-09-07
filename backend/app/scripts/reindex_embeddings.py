"""
Safe Re-indexing Utility for FactLens Chunks.
Re-generates vector embeddings using the configured Jina AI embedding model (1024 dimensions)
and updates PostgreSQL pgvector storage without data loss.
"""

import asyncio
import logging
from psycopg2.extras import RealDictCursor
from backend.app.config import get_settings
from backend.app.database import get_db_connection
from backend.app.providers.embeddings.jina import JinaEmbeddingProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("factlens.reindex")


async def reindex_all_chunks(batch_size: int = 20) -> dict[str, int]:
    """
    Fetch all chunks from database, compute 1024-d Jina embeddings,
    and update rows safely.
    """
    settings = get_settings()
    if not settings.jina_api_key:
        raise ValueError("JINA_API_KEY is required for re-indexing.")

    provider = JinaEmbeddingProvider(
        api_key=settings.jina_api_key,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
    )

    conn = get_db_connection(settings)
    conn.autocommit = True
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, text FROM public.chunks ORDER BY created_at ASC;")
            chunks = cur.fetchall()

        total = len(chunks)
        logger.info("Found %d chunks to re-index with Jina (dimension %d)...", total, provider.dimension)

        if total == 0:
            logger.info("No chunks present in database. Database is already prepared for new 1024-d embeddings.")
            return {"total": 0, "updated": 0}

        updated = 0
        for i in range(0, total, batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["text"] for c in batch]
            ids = [c["id"] for c in batch]

            logger.info("Embedding batch %d to %d of %d...", i + 1, min(i + batch_size, total), total)
            vectors = await provider.embed_documents(texts)

            with conn.cursor() as cur:
                for chunk_id, vec in zip(ids, vectors):
                    vec_str = "[" + ",".join(str(f) for f in vec) + "]"
                    cur.execute(
                        "UPDATE public.chunks SET embedding = %s::vector WHERE id = %s;",
                        (vec_str, chunk_id),
                    )
            updated += len(batch)

        logger.info("Re-indexing complete: %d/%d chunks updated.", updated, total)
        return {"total": total, "updated": updated}
    finally:
        conn.close()


if __name__ == "__main__":
    result = asyncio.run(reindex_all_chunks())
    print(f"Re-indexing result: {result}")
