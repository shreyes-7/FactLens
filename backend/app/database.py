"""
Database & pgvector search module for FactLens.
Provides connection management and vector similarity search for chunks.
"""

import json
from typing import Any
from uuid import uuid4
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
            value_text, raw_value_text, value_numeric, normalized_value_numeric, value_boolean,
            unit, normalized_unit, fact_type, period_text, period_start, period_end,
            scope, geography, segment, status, attribution, qualifiers, confidence, metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
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
                # Deduplication guard: do not insert duplicate facts for the same document
                check_query = """
                    SELECT f.id FROM public.facts f
                    LEFT JOIN public.evidence e ON f.id = e.fact_id
                    WHERE f.document_id = %s
                      AND (
                          lower(trim(f.raw_claim)) = lower(trim(%s))
                          OR (e.quote IS NOT NULL AND lower(trim(e.quote)) = lower(trim(%s)))
                      )
                    LIMIT 1;
                """
                cur.execute(
                    check_query,
                    (
                        str(fact_data["document_id"]),
                        fact_data.get("raw_claim") or "",
                        evidence_data.get("quote") or "",
                    ),
                )
                if cur.fetchone():
                    continue

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
                        fact_data.get("normalized_value_numeric"),
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


def get_all_facts(
    dataset_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Retrieve all facts optionally filtered by dataset_id."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT id, dataset_id, document_id, subject, predicate, raw_claim,
               value_text, raw_value_text, value_numeric, normalized_value_numeric,
               value_boolean, unit, normalized_unit, fact_type, period_text,
               period_start, period_end, scope, geography, segment, status,
               attribution, qualifiers, confidence, metadata
        FROM public.facts
    """
    params: list[Any] = []
    if dataset_id:
        query += " WHERE dataset_id = %s"
        params.append(dataset_id)
    query += " ORDER BY created_at ASC;"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_fact_normalization(
    fact_id: str,
    normalized_value_numeric: float | None,
    normalized_unit: str | None,
    period_start: Any = None,
    period_end: Any = None,
    settings: Settings | None = None,
) -> None:
    """Update normalized attributes on an existing fact."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    conn.autocommit = True
    query = """
        UPDATE public.facts
        SET normalized_value_numeric = %s,
            normalized_unit = %s,
            period_start = %s,
            period_end = %s,
            updated_at = now()
        WHERE id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    normalized_value_numeric,
                    normalized_unit,
                    period_start,
                    period_end,
                    fact_id,
                ),
            )
    finally:
        conn.close()


def update_fact_embedding(
    fact_id: str,
    embedding: list[float],
    settings: Settings | None = None,
) -> None:
    """Store 1024-dimensional vector embedding for a fact."""
    cfg = settings or get_settings()
    if len(embedding) != cfg.embedding_dimension:
        raise ValueError(
            f"Fact embedding dimension mismatch: got {len(embedding)}, expected {cfg.embedding_dimension}."
        )

    embedding_str = "[" + ",".join(str(f) for f in embedding) + "]"
    conn = get_db_connection(cfg)
    conn.autocommit = True
    query = """
        UPDATE public.facts
        SET embedding = %s::vector,
            updated_at = now()
        WHERE id = %s;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (embedding_str, fact_id))
    finally:
        conn.close()


def get_facts_for_matching(
    dataset_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve facts with parsed float vector embeddings for candidate matching.
    """
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT id, dataset_id, document_id, subject, predicate, raw_claim,
               value_text, raw_value_text, value_numeric, normalized_value_numeric,
               value_boolean, unit, normalized_unit, fact_type, period_text,
               period_start, period_end, scope, geography, segment, status,
               attribution, qualifiers, confidence, metadata,
               embedding::text as embedding_str
        FROM public.facts
    """
    params: list[Any] = []
    if dataset_id:
        query += " WHERE dataset_id = %s"
        params.append(dataset_id)
    query += " ORDER BY created_at ASC;"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                emb_str = r.pop("embedding_str", None)
                if emb_str and emb_str.startswith("[") and emb_str.endswith("]"):
                    r["embedding"] = [float(x) for x in emb_str[1:-1].split(",") if x.strip()]
                else:
                    r["embedding"] = None
            return rows
    finally:
        conn.close()


def find_candidate_facts_pgvector(
    fact_id: str,
    dataset_id: str,
    embedding: list[float],
    top_k: int = 10,
    min_similarity: float = 0.5,
    cross_document_only: bool = True,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """
    Execute pgvector cosine distance query to retrieve nearest neighbor facts.
    """
    cfg = settings or get_settings()
    embedding_str = "[" + ",".join(str(f) for f in embedding) + "]"

    query = """
        SELECT id, dataset_id, document_id, subject, predicate, raw_claim,
               value_numeric, normalized_value_numeric, unit, normalized_unit,
               period_text, period_start, period_end,
               (1 - (embedding <=> %s::vector)) AS similarity
        FROM public.facts
        WHERE dataset_id = %s
          AND id != %s
          AND embedding IS NOT NULL
    """
    params: list[Any] = [embedding_str, dataset_id, fact_id]

    if cross_document_only:
        query += " AND document_id != (SELECT document_id FROM public.facts WHERE id = %s)"
        params.append(fact_id)

    query += """
          AND (1 - (embedding <=> %s::vector)) >= %s
        ORDER BY (embedding <=> %s::vector) ASC
        LIMIT %s;
    """
    params.extend([embedding_str, min_similarity, embedding_str, top_k])

    conn = get_db_connection(cfg)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def insert_fact_relationship(
    relationship: dict[str, Any],
    settings: Settings | None = None,
) -> str:
    """
    Persist a verified fact relationship to public.fact_relationships.
    Enforces canonical ordering (fact_a_id < fact_b_id) and updates on conflict.
    """
    cfg = settings or get_settings()
    id_a = str(relationship["fact_a_id"])
    id_b = str(relationship["fact_b_id"])

    if id_a >= id_b:
        raise ValueError(f"Constraint violation: fact_a_id ({id_a}) must be strictly less than fact_b_id ({id_b}).")

    rel_id = str(relationship.get("id") or uuid4())
    context_json = json.dumps(relationship.get("contextual_factors") or {})

    query = """
        INSERT INTO public.fact_relationships (
            id, fact_a_id, fact_b_id, relationship_type, confidence,
            reason, contextual_factors, reasoning_method, model, prompt_version
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s::jsonb, %s, %s, %s
        )
        ON CONFLICT (fact_a_id, fact_b_id) DO UPDATE
        SET relationship_type = EXCLUDED.relationship_type,
            confidence = EXCLUDED.confidence,
            reason = EXCLUDED.reason,
            contextual_factors = EXCLUDED.contextual_factors,
            reasoning_method = EXCLUDED.reasoning_method,
            model = EXCLUDED.model,
            prompt_version = EXCLUDED.prompt_version,
            updated_at = now()
        RETURNING id;
    """

    conn = get_db_connection(cfg)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    rel_id,
                    id_a,
                    id_b,
                    relationship["relationship_type"],
                    relationship["confidence"],
                    relationship["reason"],
                    context_json,
                    relationship.get("reasoning_method", "hybrid"),
                    relationship.get("model"),
                    relationship.get("prompt_version"),
                ),
            )
            res = cur.fetchone()
            return str(res[0])
    finally:
        conn.close()


def get_fact_relationships(
    dataset_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Retrieve fact relationships, optionally filtered by dataset."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)

    query = """
        SELECT r.id, r.fact_a_id, r.fact_b_id, r.relationship_type, r.confidence,
               r.reason, r.contextual_factors, r.reasoning_method, r.model,
               r.created_at, r.updated_at,
               fa.subject as fact_a_subject, fa.predicate as fact_a_predicate, fa.raw_claim as fact_a_claim,
               fb.subject as fact_b_subject, fb.predicate as fact_b_predicate, fb.raw_claim as fact_b_claim
        FROM public.fact_relationships r
        JOIN public.facts fa ON r.fact_a_id = fa.id
        JOIN public.facts fb ON r.fact_b_id = fb.id
    """
    params: list[Any] = []
    if dataset_id:
        query += " WHERE fa.dataset_id = %s AND fb.dataset_id = %s"
        params.extend([dataset_id, dataset_id])

    query += " ORDER BY r.created_at DESC;"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_fact_evidence_quote(fact_id: str, settings: Settings | None = None) -> str | None:
    """Retrieve the primary evidence quote for a fact."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT quote FROM public.evidence
        WHERE fact_id = %s
        ORDER BY created_at ASC
        LIMIT 1;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (fact_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def get_all_datasets(settings: Settings | None = None) -> list[dict[str, Any]]:
    """Retrieve all datasets with document, fact, and relationship counts."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT 
            d.id, 
            d.name, 
            d.description, 
            d.created_at,
            (SELECT COUNT(*) FROM public.documents doc WHERE doc.dataset_id = d.id) AS document_count,
            (SELECT COUNT(*) FROM public.facts f WHERE f.dataset_id = d.id) AS fact_count,
            (
                SELECT COUNT(*) 
                FROM public.fact_relationships r
                JOIN public.facts fa ON r.fact_a_id = fa.id
                WHERE fa.dataset_id = d.id
            ) AS relationship_count
        FROM public.datasets d
        ORDER BY d.created_at DESC;
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_dataset_by_id(dataset_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Retrieve a single dataset by ID with counts."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT 
            d.id, 
            d.name, 
            d.description, 
            d.created_at,
            (SELECT COUNT(*) FROM public.documents doc WHERE doc.dataset_id = d.id) AS document_count,
            (SELECT COUNT(*) FROM public.facts f WHERE f.dataset_id = d.id) AS fact_count,
            (
                SELECT COUNT(*) 
                FROM public.fact_relationships r
                JOIN public.facts fa ON r.fact_a_id = fa.id
                WHERE fa.dataset_id = d.id
            ) AS relationship_count
        FROM public.datasets d
        WHERE d.id = %s;
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (dataset_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_all_documents(dataset_id: str | None = None, settings: Settings | None = None) -> list[dict[str, Any]]:
    """Retrieve documents optionally filtered by dataset."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT 
            d.id, 
            d.dataset_id, 
            d.filename, 
            COALESCE(d.page_count, 0) AS page_count, 
            COALESCE((d.metadata->>'file_size_bytes')::bigint, 0) AS file_size_bytes, 
            d.storage_path, 
            COALESCE((SELECT status FROM public.processing_runs pr WHERE pr.document_id = d.id ORDER BY pr.created_at DESC LIMIT 1), 'ingested') AS status, 
            d.created_at
        FROM public.documents d
    """
    params: list[Any] = []
    if dataset_id:
        query += " WHERE d.dataset_id = %s"
        params.append(dataset_id)
    query += " ORDER BY d.created_at DESC;"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_document_detail(document_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Retrieve detailed document metadata including fact counts and processing runs."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    d.id, 
                    d.dataset_id, 
                    d.filename, 
                    COALESCE(d.page_count, 0) AS page_count, 
                    COALESCE((d.metadata->>'file_size_bytes')::bigint, 0) AS file_size_bytes, 
                    d.storage_path, 
                    COALESCE((SELECT status FROM public.processing_runs pr WHERE pr.document_id = d.id ORDER BY pr.created_at DESC LIMIT 1), 'ingested') AS status, 
                    d.created_at
                FROM public.documents d
                WHERE d.id = %s;
                """,
                (document_id,),
            )
            doc = cur.fetchone()
            if not doc:
                return None
            res = dict(doc)

            # Fact count
            cur.execute("SELECT COUNT(*) AS total FROM public.facts WHERE document_id = %s;", (document_id,))
            res["total_facts_extracted"] = cur.fetchone()["total"]

            # Chunk count
            cur.execute("SELECT COUNT(*) AS total FROM public.chunks WHERE document_id = %s;", (document_id,))
            res["total_chunks"] = cur.fetchone()["total"]

            # Extracted pages tracking
            cur.execute(
                """
                SELECT DISTINCT dp.pdf_page_number
                FROM public.document_pages dp
                WHERE dp.document_id = %s
                  AND (
                    dp.id IN (SELECT page_id FROM public.evidence WHERE document_id = %s)
                    OR dp.id IN (SELECT page_id FROM public.chunks WHERE document_id = %s)
                  )
                ORDER BY dp.pdf_page_number;
                """,
                (document_id, document_id, document_id),
            )
            extracted_pages = [r["pdf_page_number"] for r in cur.fetchall() if r["pdf_page_number"] is not None]
            res["extracted_page_numbers"] = extracted_pages
            res["extracted_pages_count"] = len(extracted_pages)

            # Processing runs
            cur.execute(
                """
                SELECT id, status, pages_processed, chunks_created, facts_extracted, facts_rejected, error_code, error_message, started_at, completed_at
                FROM public.processing_runs
                WHERE document_id = %s
                ORDER BY started_at DESC
                LIMIT 10;
                """,
                (document_id,),
            )
            res["processing_runs"] = [dict(r) for r in cur.fetchall()]
            return res
    finally:
        conn.close()


def get_facts_with_evidence(
    dataset_id: str | None = None,
    document_id: str | None = None,
    category: str | None = None,
    entity: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    settings: Settings | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Retrieve facts with pagination, filtering, and joined evidence quotes and document metadata.
    Returns (total_count, facts_list).
    """
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)

    where_clauses: list[str] = []
    params: list[Any] = []

    if dataset_id:
        where_clauses.append("f.dataset_id = %s")
        params.append(dataset_id)
    if document_id:
        where_clauses.append("f.document_id = %s")
        params.append(document_id)
    if category:
        where_clauses.append("COALESCE(f.metadata->>'category', f.fact_type) = %s")
        params.append(category)
    if entity:
        where_clauses.append("f.subject ILIKE %s")
        params.append(f"%{entity}%")
    if search:
        where_clauses.append("(f.subject ILIKE %s OR f.predicate ILIKE %s OR f.raw_claim ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_query = f"SELECT COUNT(*) AS total FROM public.facts f {where_sql};"

    data_query = f"""
        SELECT 
            f.id,
            f.document_id,
            d.filename AS document_filename,
            COALESCE(dp.pdf_page_number, (f.metadata->>'page_number')::int) AS page_number,
            dp.printed_page_number,
            f.subject AS entity,
            COALESCE(f.metadata->>'category', f.fact_type) AS category,
            f.predicate,
            f.raw_claim AS raw_value,
            COALESCE(f.normalized_value_numeric, f.value_numeric) AS normalized_value,
            COALESCE(f.normalized_unit, f.unit) AS unit,
            f.period_text AS time_period,
            f.scope,
            f.status,
            f.confidence AS confidence_score,
            f.created_at
        FROM public.facts f
        LEFT JOIN public.documents d ON f.document_id = d.id
        LEFT JOIN LATERAL (
            SELECT dp.pdf_page_number, dp.printed_page_number
            FROM public.evidence e
            JOIN public.document_pages dp ON e.page_id = dp.id
            WHERE e.fact_id = f.id
            LIMIT 1
        ) dp ON true
        {where_sql}
        ORDER BY f.created_at DESC
        LIMIT %s OFFSET %s;
    """

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(count_query, params)
            total = cur.fetchone()["total"]

            cur.execute(data_query, params + [limit, offset])
            facts = [dict(r) for r in cur.fetchall()]

            # Fetch evidence for all returned facts in one batch
            if facts:
                fact_ids = [str(f["id"]) for f in facts]
                cur.execute(
                    """
                    SELECT 
                        e.id, 
                        e.fact_id, 
                        e.quote, 
                        dp.pdf_page_number AS page_number, 
                        dp.printed_page_number, 
                        e.start_offset AS char_start, 
                        e.end_offset AS char_end, 
                        e.extraction_confidence AS similarity_score
                    FROM public.evidence e
                    LEFT JOIN public.document_pages dp ON e.page_id = dp.id
                    WHERE e.fact_id = ANY(%s::uuid[])
                    ORDER BY e.created_at ASC;
                    """,
                    (fact_ids,),
                )
                evidence_by_fact: dict[str, list[dict[str, Any]]] = {}
                for ev in cur.fetchall():
                    fid = str(ev["fact_id"])
                    if fid not in evidence_by_fact:
                        evidence_by_fact[fid] = []
                    evidence_by_fact[fid].append(dict(ev))

                for f in facts:
                    fid = str(f["id"])
                    f["evidence"] = evidence_by_fact.get(fid, [])
                    if f["evidence"] and not f.get("quote"):
                        f["quote"] = f["evidence"][0]["quote"]
            return total, facts
    finally:
        conn.close()


def get_fact_detail(fact_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Retrieve full details of a fact including evidence items and source document."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)
    query = """
        SELECT 
            f.id,
            f.document_id,
            d.filename AS document_filename,
            COALESCE(dp.pdf_page_number, (f.metadata->>'page_number')::int) AS page_number,
            dp.printed_page_number,
            f.subject AS entity,
            COALESCE(f.metadata->>'category', f.fact_type) AS category,
            f.predicate,
            f.raw_claim AS raw_value,
            COALESCE(f.normalized_value_numeric, f.value_numeric) AS normalized_value,
            COALESCE(f.normalized_unit, f.unit) AS unit,
            f.period_text AS time_period,
            f.scope,
            f.status,
            f.confidence AS confidence_score,
            f.created_at
        FROM public.facts f
        LEFT JOIN public.documents d ON f.document_id = d.id
        LEFT JOIN LATERAL (
            SELECT dp.pdf_page_number, dp.printed_page_number
            FROM public.evidence e
            JOIN public.document_pages dp ON e.page_id = dp.id
            WHERE e.fact_id = f.id
            LIMIT 1
        ) dp ON true
        WHERE f.id = %s;
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (fact_id,))
            fact = cur.fetchone()
            if not fact:
                return None
            res = dict(fact)

            cur.execute(
                """
                SELECT 
                    e.id, 
                    e.quote, 
                    dp.pdf_page_number AS page_number, 
                    dp.printed_page_number, 
                    e.start_offset AS char_start, 
                    e.end_offset AS char_end, 
                    e.extraction_confidence AS similarity_score
                FROM public.evidence e
                LEFT JOIN public.document_pages dp ON e.page_id = dp.id
                WHERE e.fact_id = %s
                ORDER BY e.created_at ASC;
                """,
                (fact_id,),
            )
            res["evidence"] = [dict(r) for r in cur.fetchall()]
            if res["evidence"]:
                res["quote"] = res["evidence"][0]["quote"]
            return res
    finally:
        conn.close()


def get_relationships_detailed(
    dataset_id: str | None = None,
    relationship_type: str | None = None,
    min_confidence: float = 0.0,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Retrieve relationships with full joined Fact A and Fact B metadata and quotes."""
    cfg = settings or get_settings()
    conn = get_db_connection(cfg)

    query = """
        SELECT 
            r.id,
            r.fact_a_id,
            r.fact_b_id,
            r.relationship_type,
            r.confidence,
            r.reason AS rationale,
            r.contextual_factors,
            r.created_at,
            -- Fact A
            fa.subject AS fa_entity,
            fa.predicate AS fa_predicate,
            fa.raw_claim AS fa_raw_value,
            COALESCE(fa.normalized_value_numeric, fa.value_numeric) AS fa_normalized_value,
            COALESCE(fa.normalized_unit, fa.unit) AS fa_unit,
            fa.period_text AS fa_time_period,
            fa.scope AS fa_scope,
            fa.status AS fa_status,
            COALESCE(dpa.pdf_page_number, (fa.metadata->>'page_number')::int) AS fa_page_number,
            da.filename AS fa_document_filename,
            -- Fact B
            fb.subject AS fb_entity,
            fb.predicate AS fb_predicate,
            fb.raw_claim AS fb_raw_value,
            COALESCE(fb.normalized_value_numeric, fb.value_numeric) AS fb_normalized_value,
            COALESCE(fb.normalized_unit, fb.unit) AS fb_unit,
            fb.period_text AS fb_time_period,
            fb.scope AS fb_scope,
            fb.status AS fb_status,
            COALESCE(dpb.pdf_page_number, (fb.metadata->>'page_number')::int) AS fb_page_number,
            db.filename AS fb_document_filename,
            -- Quotes
            (SELECT quote FROM public.evidence ea WHERE ea.fact_id = fa.id ORDER BY ea.created_at ASC LIMIT 1) AS evidence_a_quote,
            (SELECT quote FROM public.evidence eb WHERE eb.fact_id = fb.id ORDER BY eb.created_at ASC LIMIT 1) AS evidence_b_quote
        FROM public.fact_relationships r
        JOIN public.facts fa ON r.fact_a_id = fa.id
        JOIN public.facts fb ON r.fact_b_id = fb.id
        LEFT JOIN public.documents da ON fa.document_id = da.id
        LEFT JOIN public.documents db ON fb.document_id = db.id
        LEFT JOIN LATERAL (
            SELECT dp.pdf_page_number FROM public.evidence ea
            JOIN public.document_pages dp ON ea.page_id = dp.id
            WHERE ea.fact_id = fa.id LIMIT 1
        ) dpa ON true
        LEFT JOIN LATERAL (
            SELECT dp.pdf_page_number FROM public.evidence eb
            JOIN public.document_pages dp ON eb.page_id = dp.id
            WHERE eb.fact_id = fb.id LIMIT 1
        ) dpb ON true
    """
    where_clauses: list[str] = []
    params: list[Any] = []

    if dataset_id:
        where_clauses.append("fa.dataset_id = %s")
        params.append(dataset_id)
    if relationship_type:
        where_clauses.append("r.relationship_type = %s")
        params.append(relationship_type)
    if min_confidence > 0.0:
        where_clauses.append("r.confidence >= %s")
        params.append(min_confidence)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY r.confidence DESC, r.created_at DESC;"

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            results = []
            for row in cur.fetchall():
                results.append({
                    "id": row["id"],
                    "fact_a_id": row["fact_a_id"],
                    "fact_b_id": row["fact_b_id"],
                    "relationship_type": row["relationship_type"],
                    "confidence": float(row["confidence"]),
                    "rationale": row["rationale"],
                    "contextual_factors": row["contextual_factors"] or {},
                    "created_at": row["created_at"],
                    "evidence_a_quote": row["evidence_a_quote"],
                    "evidence_b_quote": row["evidence_b_quote"],
                    "fact_a": {
                        "id": row["fact_a_id"],
                        "document_filename": row["fa_document_filename"],
                        "page_number": row["fa_page_number"],
                        "entity": row["fa_entity"],
                        "predicate": row["fa_predicate"],
                        "raw_value": row["fa_raw_value"],
                        "normalized_value": float(row["fa_normalized_value"]) if row["fa_normalized_value"] is not None else None,
                        "unit": row["fa_unit"],
                        "time_period": row["fa_time_period"],
                        "scope": row["fa_scope"],
                        "status": row["fa_status"],
                        "quote": row["evidence_a_quote"],
                    },
                    "fact_b": {
                        "id": row["fact_b_id"],
                        "document_filename": row["fb_document_filename"],
                        "page_number": row["fb_page_number"],
                        "entity": row["fb_entity"],
                        "predicate": row["fb_predicate"],
                        "raw_value": row["fb_raw_value"],
                        "normalized_value": float(row["fb_normalized_value"]) if row["fb_normalized_value"] is not None else None,
                        "unit": row["fb_unit"],
                        "time_period": row["fb_time_period"],
                        "scope": row["fb_scope"],
                        "status": row["fb_status"],
                        "quote": row["evidence_b_quote"],
                    },
                })
            return results
    finally:
        conn.close()




