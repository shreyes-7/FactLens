"""
Database & pgvector search module for FactLens.
Provides connection management and vector similarity search for chunks.
"""

import json
from typing import Any
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.config import Settings, get_settings


def get_db_connection(settings: Settings | None = None):
    """Create a connection to the PostgreSQL database."""
    cfg = settings or get_settings()
    if not cfg.database_url:
        raise ValueError("DATABASE_URL is not configured.")
    return psycopg2.connect(cfg.database_url)


def search_similar_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    dataset_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """
    Search chunks table using cosine similarity on pgvector embedding.
    Cosine distance operator is <=> in pgvector.
    Smaller distance = higher similarity.
    """
    cfg = settings or get_settings()
    if len(query_embedding) != cfg.embedding_dimension:
        raise ValueError(
            f"Query embedding dimension mismatch: got {len(query_embedding)}, expected {cfg.embedding_dimension}."
        )

    embedding_str = "[" + ",".join(str(f) for f in query_embedding) + "]"

    query = """
        SELECT
            c.id,
            c.document_id,
            c.page_id,
            c.chunk_index,
            c.text,
            c.metadata,
            (c.embedding <=> %s::vector) AS distance
        FROM public.chunks c
    """
    params = [embedding_str]

    if dataset_id:
        query += """
            JOIN public.documents d ON c.document_id = d.id
            WHERE d.dataset_id = %s
        """
        params.append(dataset_id)

    query += """
        ORDER BY distance ASC
        LIMIT %s;
    """
    params.append(top_k)

    conn = get_db_connection(cfg)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_chunk(
    chunk_id: str,
    document_id: str,
    page_id: str,
    chunk_index: int,
    text: str,
    embedding: list[float],
    metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> None:
    """Insert a chunk with its 1024-dimensional vector embedding."""
    cfg = settings or get_settings()
    if len(embedding) != cfg.embedding_dimension:
        raise ValueError(
            f"Chunk embedding dimension mismatch: got {len(embedding)}, expected {cfg.embedding_dimension}."
        )

    embedding_str = "[" + ",".join(str(f) for f in embedding) + "]"
    meta_json = json.dumps(metadata or {})

    query = """
        INSERT INTO public.chunks (id, document_id, page_id, chunk_index, text, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)
        ON CONFLICT (page_id, chunk_index) DO UPDATE
        SET text = EXCLUDED.text,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata;
    """
    conn = get_db_connection(cfg)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(query, (chunk_id, document_id, page_id, chunk_index, text, embedding_str, meta_json))
    finally:
        conn.close()
