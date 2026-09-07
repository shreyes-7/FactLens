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


def get_document_pages(
    document_id: str,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Retrieve all pages for a document ordered by pdf_page_number."""
    cfg = settings or get_settings()
    query = """
        SELECT id, document_id, pdf_page_number, printed_page_number, text, metadata
        FROM public.document_pages
        WHERE document_id = %s
        ORDER BY pdf_page_number ASC;
    """
    conn = get_db_connection(cfg)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (document_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def insert_chunks_batch(
    chunks: list[dict[str, Any]],
    settings: Settings | None = None,
) -> list[str]:
    """Batch insert chunks with embeddings. Returns list of actual persisted chunk UUID strings."""
    if not chunks:
        return []

    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    conn.autocommit = True

    query = """
        INSERT INTO public.chunks (id, document_id, page_id, chunk_index, text, start_offset, end_offset, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
        ON CONFLICT (page_id, chunk_index) DO UPDATE
        SET text = EXCLUDED.text,
            start_offset = EXCLUDED.start_offset,
            end_offset = EXCLUDED.end_offset,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata
        RETURNING id;
    """

    persisted_ids: list[str] = []
    try:
        with conn.cursor() as cur:
            for c in chunks:
                emb = c.get("embedding")
                emb_str = ("[" + ",".join(str(f) for f in emb) + "]") if emb else None
                meta_json = json.dumps(c.get("metadata") or {})
                cur.execute(
                    query,
                    (
                        str(c["id"]),
                        str(c["document_id"]),
                        str(c["page_id"]),
                        c["chunk_index"],
                        c["text"],
                        c.get("start_offset"),
                        c.get("end_offset"),
                        emb_str,
                        meta_json,
                    ),
                )
                row = cur.fetchone()
                actual_id = str(row[0])
                c["id"] = actual_id
                persisted_ids.append(actual_id)
    finally:
        conn.close()

    return persisted_ids



def insert_facts_and_evidence(
    items: list[tuple[dict[str, Any], dict[str, Any]]],
    settings: Settings | None = None,
) -> tuple[int, int]:
    """
    Insert facts and their corresponding evidence links in a single transaction.
    Takes a list of tuples: (fact_dict, evidence_dict).
    Returns (facts_count, evidence_count).
    """
    if not items:
        return 0, 0

    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    conn.autocommit = False

    fact_query = """
        INSERT INTO public.facts (
            id, dataset_id, document_id, subject, predicate, raw_claim,
            value_text, raw_value_text, value_numeric, value_boolean,
            unit, normalized_unit, fact_type, period_text, period_start, period_end,
            scope, geography, segment, status, attribution, qualifiers, confidence, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb
        );
    """

    evidence_query = """
        INSERT INTO public.evidence (
            id, fact_id, document_id, page_id, chunk_id, quote,
            start_offset, end_offset, extraction_method, extraction_confidence, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s::jsonb
        );
    """

    facts_inserted = 0
    evidence_inserted = 0

    try:
        with conn.cursor() as cur:
            for fact_data, evidence_data in items:
                # 1. Insert Fact
                cur.execute(
                    fact_query,
                    (
                        str(fact_data["id"]),
                        str(fact_data["dataset_id"]),
                        str(fact_data["document_id"]),
                        fact_data["subject"],
                        fact_data["predicate"],
                        fact_data["raw_claim"],
                        fact_data.get("value_text"),
                        fact_data.get("raw_value_text"),
                        fact_data.get("value_numeric"),
                        fact_data.get("value_boolean"),
                        fact_data.get("unit"),
                        fact_data.get("normalized_unit"),
                        fact_data.get("fact_type", "NUMERICAL"),
                        fact_data.get("period_text"),
                        fact_data.get("period_start"),
                        fact_data.get("period_end"),
                        fact_data.get("scope"),
                        fact_data.get("geography"),
                        fact_data.get("segment"),
                        fact_data.get("status"),
                        fact_data.get("attribution"),
                        json.dumps(fact_data.get("qualifiers") or {}),
                        fact_data.get("confidence", 1.0),
                        json.dumps(fact_data.get("metadata") or {}),
                    ),
                )
                facts_inserted += 1

                # 2. Insert Evidence
                cur.execute(
                    evidence_query,
                    (
                        str(evidence_data["id"]),
                        str(evidence_data["fact_id"]),
                        str(evidence_data["document_id"]),
                        str(evidence_data["page_id"]),
                        str(evidence_data["chunk_id"]) if evidence_data.get("chunk_id") else None,
                        evidence_data["quote"],
                        evidence_data.get("start_offset"),
                        evidence_data.get("end_offset"),
                        evidence_data.get("extraction_method", "groq_structured_extraction"),
                        evidence_data.get("extraction_confidence", 1.0),
                        json.dumps(evidence_data.get("metadata") or {}),
                    ),
                )
                evidence_inserted += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return facts_inserted, evidence_inserted


def update_processing_run_counts(
    run_id: str,
    chunks_created: int = 0,
    facts_extracted: int = 0,
    facts_rejected: int = 0,
    status: str | None = None,
    settings: Settings | None = None,
) -> None:
    """Increment metric counters and optionally update status on a processing_run record."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    conn.autocommit = True

    query = """
        UPDATE public.processing_runs
        SET chunks_created = chunks_created + %s,
            facts_extracted = facts_extracted + %s,
            facts_rejected = facts_rejected + %s
    """
    params = [chunks_created, facts_extracted, facts_rejected]

    if status:
        query += ", status = %s"
        params.append(status)

    query += " WHERE id = %s;"
    params.append(run_id)

    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
    finally:
        conn.close()

